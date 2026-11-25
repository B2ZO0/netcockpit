"""Checks a running stack (used by CI): agents can push through the gateway with the agent token, nobody else can,
and nothing else is reachable from the network.

    python3 tests/stack_check.py <non-loopback address of this host>              # AGENT_AUTH=required (default)
    python3 tests/stack_check.py <non-loopback address of this host> --optional   # AGENT_AUTH=optional

Run from the NetCockpit folder (the agent token is read from .env). Start the stack first, without the cockpit:
docker compose up -d prometheus loki alertmanager agent-gateway
Not a unit test (needs the containers): unittest discovery ignores this file."""
import json
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

IP = sys.argv[1]
OPTIONAL = "--optional" in sys.argv[2:]
TOKEN = [line.split("=", 1)[1].strip() for line in open(".env", encoding="utf-8") if line.startswith("AGENT_TOKEN=")][-1]
AUTH = {"Authorization": f"Bearer {TOKEN}"}
WRONG = [{"Authorization": "Bearer not-the-agent-token-0000"}, {"Authorization": f"Bearer {TOKEN.swapcase()}"},
         {"Authorization": f"Bearer {TOKEN}x"}, {"Authorization": f"Basic {TOKEN}"}, {"Authorization": TOKEN}]
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
REMOTE_WRITE = {"Content-Type": "application/x-protobuf", "Content-Encoding": "snappy", "X-Prometheus-Remote-Write-Version": "0.1.0"}
LOKI_PUSH = {"Content-Type": "application/json"}


def push_metric(name, value, headers):
    return call(f"http://{IP}:9090/api/v1/write", data=snappy_block(write_request(name, value)), method="POST",
                headers={**REMOTE_WRITE, **headers})


def push_log(text, headers):
    body = {"streams": [{"stream": {"job": "ci"}, "values": [[str(time.time_ns()), text]]}]}
    return call(f"http://{IP}:3100/loki/api/v1/push", data=json.dumps(body).encode(), method="POST", headers={**LOKI_PUSH, **headers})


def prom_has(name):
    q = "http://127.0.0.1:9091/api/v1/query?" + urllib.parse.urlencode({"query": name})
    return bool(json.loads(call(q)[1])["data"]["result"])


def loki_has(text):
    q = "http://127.0.0.1:3101/loki/api/v1/query_range?" + urllib.parse.urlencode({"query": '{job="ci"}', "limit": 100})
    return text in call(q)[1]


# 0. the agent token decides who can push
for i, headers in enumerate(WRONG):
    status, body = push_metric(f"netcockpit_ci_wrong_token_{i}", 1, headers)
    check(status == 401, f"metrics with a wrong token refused on {IP}:9090 ({status})")
    status, body = push_log(f"netcockpit-ci-wrong-token-{i}", headers)
    check(status == 401, f"logs with a wrong token refused on {IP}:3100 ({status})")
status, _ = push_metric("netcockpit_ci_no_token", 1, {})
check(status in ((200, 204) if OPTIONAL else (401,)),
      f"metrics without a token {'accepted (AGENT_AUTH=optional)' if OPTIONAL else 'refused'} ({status})")
nolog = f"netcockpit-ci-no-token-{int(time.time())}"
status, _ = push_log(nolog, {})
check(status == (204 if OPTIONAL else 401), f"logs without a token {'accepted (AGENT_AUTH=optional)' if OPTIONAL else 'refused'} ({status})")
if OPTIONAL:
    status, _ = push_metric("netcockpit_ci_optional", 7, AUTH)
    check(status in (200, 204), f"metrics with the token still accepted ({status})")
    print("stack check (AGENT_AUTH=optional) passed")
    sys.exit(0)

# 1. metrics pushed by an agent reach Prometheus
status, body = push_metric("netcockpit_ci_gateway", 42, AUTH)
check(status in (200, 204), f"agent metrics with the token accepted on {IP}:9090 ({status} {body[:80]})")
query = "http://127.0.0.1:9091/api/v1/query?" + urllib.parse.urlencode({"query": "netcockpit_ci_gateway"})
for _ in range(15):
    result = json.loads(call(query)[1])["data"]["result"]
    if result:
        break
    time.sleep(2)
check(bool(result) and result[0]["value"][1] == "42", "metric readable on the host (127.0.0.1:9091)")

# 2. logs pushed by an agent reach Loki
line = f"netcockpit-ci-gateway-{int(time.time())}"
status, body = push_log(line, AUTH)
check(status == 204, f"agent logs with the token accepted on {IP}:3100 ({status} {body[:80]})")
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
    for headers in ({}, AUTH):   # the agent token opens the two push endpoints, nothing else
        status, body = call(url, data=b"" if method == "POST" else None, method=method, headers=headers)
        check(status == 403 and "nginx" in body, f"{method} {url} refused by the gateway{' (with the token)' if headers else ''} ({status})")

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
check(not any(prom_has(f"netcockpit_ci_wrong_token_{i}") for i in range(len(WRONG))) and not prom_has("netcockpit_ci_no_token"),
      "nothing sent without the right token reached Prometheus")
check(not loki_has("netcockpit-ci-wrong-token") and not loki_has(nolog), "nothing sent without the right token reached Loki")
print("stack check passed")
