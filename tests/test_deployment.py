"""Deployment files: what the stack exposes on the network stays limited to what NetCockpit needs."""
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def compose(name="docker-compose.yml"):
    return yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))


class Deployment(unittest.TestCase):
    def test_prometheus_has_no_http_control_endpoints(self):
        # Agents only need remote write; setup.sh restarts Prometheus with docker compose.
        cmd = compose()["services"]["prometheus"]["command"]
        self.assertIn("--web.enable-remote-write-receiver", cmd)
        for flag in ("--web.enable-lifecycle", "--web.enable-admin-api"):
            self.assertNotIn(flag, cmd)

    def test_loki_refuses_log_deletion_but_keeps_retention(self):
        loki = yaml.safe_load((ROOT / "loki" / "loki.yml").read_text(encoding="utf-8"))
        self.assertEqual(loki["limits_config"].get("deletion_mode"), "disabled")
        self.assertTrue(loki["compactor"]["retention_enabled"])
        self.assertEqual(loki["limits_config"]["retention_period"], "30d")

    def test_alertmanager_listens_on_the_host_only(self):
        self.assertEqual(compose()["services"]["alertmanager"]["ports"], ["127.0.0.1:9093:9093"])


class LocalImages(unittest.TestCase):
    def test_images_built_here_can_only_come_from_this_machine(self):
        # "localhost/" is a registry name: no public registry can ever serve this image,
        # even to "docker compose pull" or an automatic image updater.
        for name in ("docker-compose.yml", "docker-compose.demo.yml"):
            for svc, conf in compose(name)["services"].items():
                if "build" in conf:
                    self.assertTrue(conf.get("image", "").startswith("localhost/"), f"{name}: {svc}")

    def test_setup_and_ci_use_the_local_only_name(self):
        setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
        self.assertIn('docker tag "$ref" localhost/netcockpit/cockpit:local', setup)
        self.assertIn("localhost/netcockpit/cockpit:local python /app/app/configure.py", setup)
        self.assertNotIn(" netcockpit/cockpit:local python", setup)
        wf = (ROOT / ".github" / "workflows" / "image.yml").read_text(encoding="utf-8")
        self.assertNotIn(" netcockpit/cockpit:test", wf)


class PinnedVersions(unittest.TestCase):
    """Every image of the stack has a tested version: an update moves to it, a new install gets it."""

    def test_no_image_defaults_to_latest(self):
        for svc, conf in compose()["services"].items():
            image = conf["image"]
            if "build" in conf:
                continue
            # ${PROMETHEUS_VERSION:-v3.16.0} -> v3.16.0 (what you get without a setting in .env)
            resolved = re.sub(r"\$\{[A-Z0-9_]+:-([^}]*)\}", r"\1", image)
            self.assertNotIn("${", resolved, f"{svc}: {image} has no default version")
            name, _, tag = resolved.rpartition(":")
            self.assertTrue(name and tag, f"{svc}: {image} has no tag")
            self.assertNotEqual(tag, "latest", f"{svc}: {image}")
            self.assertRegex(tag, r"\d", f"{svc}: {image}")

    def test_update_downloads_the_versions_of_the_release(self):
        setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
        self.assertIn("export NETCOCKPIT_UPDATING=1", setup)
        start = setup.index("# ------------------------------------------------------------------ 5. démarrage")
        pull = setup.index("docker compose pull --quiet --ignore-buildable", start)
        self.assertLess(pull, setup.index("docker compose up -d", start))


class AgentGateway(unittest.TestCase):
    """From the network, 9090 and 3100 only take what agents send; reading and administering stay on the host."""

    def test_only_these_ports_are_reachable_from_the_network(self):
        public = {}
        for svc, conf in compose()["services"].items():
            for port in conf.get("ports", []):
                if not str(port).startswith("127.0.0.1:"):
                    public.setdefault(svc, []).append(str(port))
        self.assertEqual(public, {
            "agent-gateway": ["9090:9090", "3100:3100"],
            "syslog": ["514:1514/udp", "514:1514/tcp"],
            "grafana": ["3000:3000"],
            "zabbix-server": ["10051:10051"],
            "zabbix-web": ["${ZABBIX_WEB_PORT:-8081}:8080"],
        })

    def test_prometheus_and_loki_listen_on_the_host_only(self):
        services = compose()["services"]
        self.assertEqual(services["prometheus"]["ports"], ["127.0.0.1:9091:9090"])
        self.assertEqual(services["loki"]["ports"], ["127.0.0.1:3101:3100"])
        env = services["cockpit"]["environment"]
        self.assertEqual(env["PROMETHEUS_URL"], "http://127.0.0.1:9091")
        self.assertEqual(env["LOKI_URL"], "http://127.0.0.1:3101")

    def test_gateway_is_pinned_and_starts_after_prometheus_and_loki(self):
        gw = compose()["services"]["agent-gateway"]
        self.assertRegex(gw["image"], r"^nginx:\$\{NGINX_VERSION:-1\.\d+\.\d+-alpine\}$")
        self.assertEqual(sorted(gw["depends_on"]), ["loki", "prometheus"])
        self.assertIn("./gateway/nginx.conf:/etc/nginx/nginx.conf:ro", gw["volumes"])

    def test_gateway_only_forwards_agent_pushes(self):
        conf = (ROOT / "gateway" / "nginx.conf").read_text(encoding="utf-8")
        code = "\n".join(line.split("#", 1)[0] for line in conf.splitlines())
        locations = re.findall(r"location\s+(=?)\s*(\S+)\s*\{", code)
        self.assertEqual(sorted(locations), [("", "/"), ("", "/"), ("=", "/api/v1/write"), ("=", "/loki/api/v1/push")])
        self.assertEqual(code.count("limit_except POST { deny all; }"), 2)
        self.assertEqual(re.findall(r"proxy_pass\s+([^;]+);", code), ["$prometheus", "$loki"])
        self.assertIn("set $prometheus http://prometheus:9090;", code)
        self.assertIn("set $loki http://loki:3100;", code)
        self.assertEqual(code.count("return 403;"), 2)
        self.assertRegex(code, r"resolver 127\.0\.0\.11\b")
        self.assertIn("server_tokens off;", code)


class Grafana(unittest.TestCase):
    def test_plugins_are_installed_before_provisioning(self):
        # With the background installer, provisioning the Zabbix app failed on the first start and Grafana exited.
        env = compose()["services"]["grafana"]["environment"]
        self.assertNotIn("GF_PLUGINS_PREINSTALL", env)
        self.assertIn("alexanderzobnin-zabbix-app", env["GF_PLUGINS_PREINSTALL_SYNC"])
        self.assertIn("yesoreyeram-infinity-datasource", env["GF_PLUGINS_PREINSTALL_SYNC"])


class CockpitPrivileges(unittest.TestCase):
    def test_cockpit_can_send_probes_but_not_change_the_host_network(self):
        # nmap and traceroute need raw packets (NET_RAW); NET_ADMIN would let the container
        # reconfigure the host's interfaces, routes and firewall (network_mode: host). CI checks discovery without it.
        cockpit = compose()["services"]["cockpit"]
        self.assertEqual(cockpit["network_mode"], "host")
        self.assertEqual(cockpit["cap_add"], ["NET_RAW"])
        self.assertNotIn("privileged", cockpit)

    def test_ci_checks_discovery_with_these_capabilities(self):
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("--cap-add NET_RAW localhost/netcockpit/cockpit:local", ci)
        self.assertNotIn("--cap-add NET_ADMIN", ci)


if __name__ == "__main__":
    unittest.main()
