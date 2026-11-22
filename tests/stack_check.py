"""Checks a running stack (used by CI): agents can push through the gateway, nothing else is reachable from the network.

    python3 tests/stack_check.py <non-loopback address of this host>

Start the stack first, without the cockpit: docker compose up -d prometheus loki alertmanager agent-gateway
Not a unit test (needs the containers): unittest discovery ignores this file."""
import json
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

IP = sys.argv[1]
OPEN = urllib.request.build_opener(urllib.request.ProxyHandler({})).open   # straight to this host, never through a proxy


def call(url, data=None, headers=None, method=None, timeout=10):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with OPEN(req, timeout=timeout) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def wait_ready(url, tries=90):
    for _ in range(tries):
        try:
            if call(url)[0] == 200:
                return
        except OSError:
            pass
        time.sleep(2)
    sys.exit(f"FAIL not ready: {url}")


def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what, flush=True)
    if not ok:
        sys.exit(1)


# ---------------------------------------------------------------- a real remote-write request, without libraries
def varint(n):
    out = b""
    while True:
        low, n = n & 0x7F, n >> 7
        if not n:
            return out + bytes([low])
        out += bytes([low | 0x80])


def field(number, wire, payload):
    key = varint(number << 3 | wire)
    return key + (varint(len(payload)) + payload if wire == 2 else payload)


def snappy_block(data):
    """Snappy block format with literals only: valid input for any snappy decoder."""
    out = varint(len(data))
    for i in range(0, len(data), 65536):
        chunk = data[i:i + 65536]
        n = len(chunk) - 1
        out += bytes([n << 2]) if n < 60 else bytes([60 << 2, n]) if n < 256 else bytes([61 << 2]) + n.to_bytes(2, "little")
        out += chunk
    return out


def write_request(name, value):
    label = lambda k, v: field(1, 2, field(1, 2, k.encode()) + field(2, 2, v.encode()))
    sample = field(1, 1, struct.pack("<d", value)) + field(2, 0, varint(int(time.time() * 1000)))
    return field(1, 2, label("__name__", name) + label("job", "ci") + field(2, 2, sample))


wait_ready("http://127.0.0.1:9091/-/ready")
wait_ready("http://127.0.0.1:3101/ready")

# 1. metrics pushed by an agent reach Prometheus
status, body = call(f"http://{IP}:9090/api/v1/write", data=snappy_block(write_request("netcockpit_ci_gateway", 42)), method="POST",
                    headers={"Content-Type": "application/x-protobuf", "Content-Encoding": "snappy",
                             "X-Prometheus-Remote-Write-Version": "0.1.0"})
check(status in (200, 204), f"agent metrics accepted on {IP}:9090 ({status} {body[:80]})")
query = "http://127.0.0.1:9091/api/v1/query?" + urllib.parse.urlencode({"query": "netcockpit_ci_gateway"})
for _ in range(15):
    result = json.loads(call(query)[1])["data"]["result"]
    if result:
        break
    time.sleep(2)
check(bool(result) and result[0]["value"][1] == "42", "metric readable on the host (127.0.0.1:9091)")

# 2. logs pushed by an agent reach Loki
line = f"netcockpit-ci-gateway-{int(time.time())}"
push = {"streams": [{"stream": {"job": "ci"}, "values": [[str(time.time_ns()), line]]}]}
status, body = call(f"http://{IP}:3100/loki/api/v1/push", data=json.dumps(push).encode(), method="POST",
                    headers={"Content-Type": "application/json"})
check(status == 204, f"agent logs accepted on {IP}:3100 ({status} {body[:80]})")
logs = "http://127.0.0.1:3101/loki/api/v1/query_range?" + urllib.parse.urlencode({"query": '{job="ci"}', "limit": 10})
found = False
for _ in range(30):
    status, body = call(logs)
    if line in body:
        found = True
        break
    time.sleep(2)
check(found, "log line readable on the host (127.0.0.1:3101)")

# 3. from the network, everything else is refused by the gateway itself
refused = [("GET", f"http://{IP}:9090/"), ("GET", f"http://{IP}:9090/graph"), ("GET", f"http://{IP}:9090/-/ready"),
           ("GET", f"http://{IP}:9090/api/v1/query?query=up"), ("GET", f"http://{IP}:9090/api/v1/status/config"),
           ("GET", f"http://{IP}:9090/federate?match%5B%5D=up"), ("GET", f"http://{IP}:9090/api/v1/write"),
           ("POST", f"http://{IP}:9090/-/quit"), ("POST", f"http://{IP}:9090/-/reload"),
           ("POST", f"http://{IP}:9090/api/v1/admin/tsdb/delete_series?match%5B%5D=up"),
           ("GET", f"http://{IP}:3100/ready"), ("GET", f"http://{IP}:3100/metrics"), ("GET", f"http://{IP}:3100/config"),
           ("GET", f"http://{IP}:3100/loki/api/v1/labels"), ("GET", f"http://{IP}:3100/loki/api/v1/push"),
           ("GET", f"http://{IP}:3100/loki/api/v1/query_range?query=%7Bjob%3D%22ci%22%7D"),
           ("GET", f"http://{IP}:3100/loki/api/v1/delete"),
           ("POST", f"http://{IP}:3100/loki/api/v1/delete?query=%7Bjob%3D%22ci%22%7D&start=0"),
           ("POST", f"http://{IP}:3100/ingester/shutdown"), ("POST", f"http://{IP}:3100/flush")]
for method, url in refused:
    status, body = call(url, data=b"" if method == "POST" else None, method=method)
    check(status == 403 and "nginx" in body, f"{method} {url} refused by the gateway ({status})")

# 4. Prometheus and Loki themselves only listen on the host
for port in (9091, 3101):
    try:
        call(f"http://{IP}:{port}/", timeout=5)
        reachable = True
    except OSError:
        reachable = False
    check(not reachable, f"{IP}:{port} not reachable from the network")

# 5. what agents pushed is still there (nothing above deleted or stopped anything)
check(bool(json.loads(call(query)[1])["data"]["result"]), "metric still there after the refused requests")
check(line in call(logs)[1], "log line still there after the refused requests")
print("stack check passed")
