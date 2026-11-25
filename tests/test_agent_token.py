"""Agent token: only agents installed with the token can push metrics and logs through the gateway.

The gateway itself (nginx) is checked on a running stack by tests/stack_check.py in CI; these tests cover what
generates its rule, how setup.sh introduces the token without cutting off agents already installed, and the agents."""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import render_config  # noqa: E402

TOKEN = "Ab3dEf6hIj9kLm2nOp5qRs8t"


def gateway_rule(**env):
    return render_config.agent_gateway(env)


class GatewayRule(unittest.TestCase):
    def test_required_accepts_the_token_only(self):
        text, mode = gateway_rule(AGENT_TOKEN=TOKEN)
        self.assertEqual(mode, "required")
        code = [line.split("#", 1)[0].strip() for line in text.splitlines() if line.split("#", 1)[0].strip()]
        self.assertEqual(code, ["map $http_authorization $agent_denied {", "default 1;", f'"~^Bearer {TOKEN}$" 0;', "}"])

    def test_the_token_is_matched_with_its_case(self):
        # nginx compares plain map strings without case; an anchored regular expression keeps the case
        text, _ = gateway_rule(AGENT_TOKEN=TOKEN)
        self.assertRegex(text, r'"~\^Bearer [A-Za-z0-9_-]+\$" 0;')
        self.assertNotIn("~*", text)

    def test_optional_also_accepts_agents_without_a_token_never_a_wrong_one(self):
        text, mode = gateway_rule(AGENT_TOKEN=TOKEN, AGENT_AUTH="optional")
        self.assertEqual(mode, "optional")
        self.assertIn('    "" 0;', text)
        self.assertIn("default 1;", text)

    def test_missing_or_unsafe_tokens_are_refused(self):
        for bad in ("", "short", 'abcdefghijklmnop" 0; } server { listen 80', "abcdefghijklmnop$x", "abcdefghijklmnop\n",
                    "abcdefghij klmnop", "a" * 129, "abcdefghijklmnop;"):
            with self.assertRaises(SystemExit, msg=repr(bad)):
                gateway_rule(AGENT_TOKEN=bad)

    def test_unknown_mode_is_refused(self):
        with self.assertRaises(SystemExit):
            gateway_rule(AGENT_TOKEN=TOKEN, AGENT_AUTH="off")

    def test_rendered_next_to_the_other_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(f"AGENT_TOKEN={TOKEN}\n", encoding="utf-8")
            render_config.render(root)
            conf = root / "secrets" / "agent-gateway.conf"
            self.assertEqual(conf.stat().st_mode & 0o777, 0o644)          # read through a file mount by nginx
            self.assertEqual((root / "secrets").stat().st_mode & 0o777, 0o700)
            self.assertIn(TOKEN, conf.read_text(encoding="utf-8"))


class Gateway(unittest.TestCase):
    def setUp(self):
        conf = (ROOT / "gateway" / "nginx.conf").read_text(encoding="utf-8")
        self.code = "\n".join(line.split("#", 1)[0] for line in conf.splitlines())

    def test_both_push_endpoints_check_the_token(self):
        for path in ("/api/v1/write", "/loki/api/v1/push"):
            block = re.search(r"location = " + re.escape(path) + r" \{(.*?)\n        \}", self.code, re.S).group(1)
            self.assertIn("if ($agent_denied) { return 401; }", block, path)
            # the token is checked before anything is forwarded
            self.assertLess(block.index("$agent_denied"), block.index("proxy_pass"), path)

    def test_rule_is_included_and_the_token_is_not_forwarded(self):
        self.assertIn("include /etc/nginx/agent-token.conf;", self.code)
        self.assertIn('proxy_set_header Authorization "";', self.code)
        self.assertNotRegex(self.code, r"location[^{]*\{[^}]*proxy_set_header")   # would drop the http-level headers

    def test_compose_mounts_the_rule_read_only(self):
        services = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))["services"]
        binds = [v for v in services["agent-gateway"]["volumes"] if isinstance(v, dict)]
        self.assertEqual(binds, [{"type": "bind", "source": "./secrets/agent-gateway.conf", "target": "/etc/nginx/agent-token.conf",
                                  "read_only": True, "bind": {"create_host_path": False}}])
        cockpit_env = services["cockpit"]["environment"]
        self.assertNotIn("AGENT_TOKEN", cockpit_env)                  # the cockpit only knows the mode
        self.assertEqual(cockpit_env["AGENT_AUTH"], "${AGENT_AUTH:-required}")


def env_merge_block():
    """The part of setup.sh that creates .env or adds new settings to it."""
    src = (ROOT / "setup.sh").read_text(encoding="utf-8")
    start = src.index('NEW_ENV=""')
    end = src.index("chmod 600 .env\n", src.index("PY\n", start)) + len("chmod 600 .env\n")
    helpers = re.search(r"^rand\(\) \{.*?\}$", src, re.M).group(0)
    return "set -euo pipefail\nsay() { printf '%s\\n' \"$2\"; }\nok() { printf '%s\\n' \"$(say \"$1\" \"$2\")\"; }\n" \
           + helpers + "\nHOST_IP=192.0.2.10\n" + src[start:end]


class SetupIntroducesTheToken(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / ".env.example").write_text((ROOT / ".env.example").read_text(encoding="utf-8"), encoding="utf-8")
        (self.dir / "merge.sh").write_text(env_merge_block(), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_setup(self):
        subprocess.run(["bash", "merge.sh"], cwd=self.dir, check=True, capture_output=True, text=True)
        return render_config.load_env(self.dir / ".env")

    def test_new_install_requires_the_token(self):
        env = self.run_setup()
        self.assertEqual(env["AGENT_AUTH"], "required")
        self.assertRegex(env["AGENT_TOKEN"], r"^[A-Za-z0-9]{24}$")
        render_config.agent_gateway(env)                              # a token the gateway rule accepts

    def test_update_keeps_agents_installed_without_the_token(self):
        (self.dir / ".env").write_text("TZ=Europe/Paris\nCOCKPIT_PASSWORD=kept\n", encoding="utf-8")
        env = self.run_setup()
        self.assertEqual(env["AGENT_AUTH"], "optional")
        self.assertRegex(env["AGENT_TOKEN"], r"^[A-Za-z0-9]{24}$")
        self.assertEqual(env["COCKPIT_PASSWORD"], "kept")

    def test_token_and_choice_are_kept_on_later_runs(self):
        first = self.run_setup()
        again = self.run_setup()
        self.assertEqual(again["AGENT_TOKEN"], first["AGENT_TOKEN"])
        self.assertEqual(again["AGENT_AUTH"], "required")
        text = (self.dir / ".env").read_text(encoding="utf-8").replace("AGENT_AUTH=required", "AGENT_AUTH=optional")
        (self.dir / ".env").write_text(text, encoding="utf-8")
        self.assertEqual(self.run_setup()["AGENT_AUTH"], "optional")

    def test_gateway_restarts_with_the_stack(self):
        src = (ROOT / "setup.sh").read_text(encoding="utf-8")
        self.assertRegex(src, r"docker compose restart [^\n]*agent-gateway")   # nginx reads its rule at start only


INSTALL = (ROOT / "agents" / "linux" / "install.sh").read_text(encoding="utf-8")


def linux_args(*args, env=None):
    """Runs the argument handling of the Linux installer (everything before it needs root)."""
    head = INSTALL[:INSTALL.index('[[ $EUID -ne 0 ]]')] + 'echo "SERVER=$SERVER NAME=$NAME TOKEN=$TOKEN"\n'
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
        f.write(head)
    try:
        return subprocess.run(["bash", f.name, *args], capture_output=True, text=True, env={**os.environ, **(env or {})})
    finally:
        os.unlink(f.name)


class LinuxAgent(unittest.TestCase):
    def test_token_after_the_address_as_in_the_setup_screen(self):
        r = linux_args("192.0.2.10", "--token", TOKEN)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"SERVER=192.0.2.10 NAME={os.uname().nodename.split('.')[0]} TOKEN={TOKEN}", r.stdout)

    def test_name_and_token_in_any_order(self):
        r = linux_args("--token=" + TOKEN, "192.0.2.10", "srv-app01")
        self.assertIn(f"SERVER=192.0.2.10 NAME=srv-app01 TOKEN={TOKEN}", r.stdout)
        r = linux_args("192.0.2.10", env={"NETCOCKPIT_AGENT_TOKEN": TOKEN})
        self.assertIn(f"TOKEN={TOKEN}", r.stdout)

    def test_old_command_without_token_still_works_with_a_warning(self):
        r = linux_args("192.0.2.10", "srv-app01")
        self.assertEqual(r.returncode, 0)
        self.assertIn("SERVER=192.0.2.10 NAME=srv-app01 TOKEN=", r.stdout)
        self.assertIn("AGENT_AUTH=optional", r.stdout)

    def test_placeholder_left_in_the_command_is_refused(self):
        r = linux_args("192.0.2.10", "--token", "<AGENT_TOKEN>")
        self.assertEqual(r.returncode, 1)
        self.assertIn("grep AGENT_TOKEN=", r.stdout)
        self.assertNotIn("SERVER=", r.stdout)

    def test_token_lives_in_a_private_file_not_in_the_config(self):
        self.assertIn('chgrp alloy "${TOKEN_FILE}.new"', INSTALL)   # stays root's file: alloy can read it, not change it
        self.assertIn('chmod 640 "${TOKEN_FILE}.new"', INSTALL)
        self.assertIn("umask 077", INSTALL)
        config = re.search(r"cat > /etc/alloy/config.alloy <<EOF\n(.*?)\nEOF\n", INSTALL, re.S).group(1)
        self.assertNotIn("TOKEN}", config.replace("TOKEN_FILE}", ""))
        self.assertEqual(config.count("${AUTH}"), 2)                   # metrics and logs
        self.assertIn('AUTH="bearer_token_file = \\"${TOKEN_FILE}\\""', INSTALL)


class WindowsAgent(unittest.TestCase):
    PS1 = (ROOT / "agents" / "windows" / "install.ps1").read_text(encoding="utf-8")

    def test_token_parameter_checked_and_stored_apart(self):
        self.assertIn("[string]$Token = $env:NETCOCKPIT_AGENT_TOKEN", self.PS1)
        self.assertIn("$Token -notmatch '^[A-Za-z0-9_-]{16,128}$'", self.PS1)
        self.assertIn("/inheritance:r", self.PS1)
        config = re.search(r"\$cfg = @'\n(.*?)\n'@", self.PS1, re.S).group(1)
        self.assertEqual(config.count("__AUTH__"), 2)
        self.assertNotIn("Token", config)


class SetupScreen(unittest.TestCase):
    def test_commands_carry_the_token_and_the_token_never_reaches_the_browser(self):
        views = (ROOT / "cockpit" / "static" / "views.js").read_text(encoding="utf-8")
        self.assertIn("-Token '<AGENT_TOKEN>'", views)
        self.assertIn("--token '<AGENT_TOKEN>'", views)
        main = (ROOT / "cockpit" / "app" / "main.py").read_text(encoding="utf-8")
        self.assertNotIn("AGENT_TOKEN", main)
        self.assertNotIn("AGENT_TOKEN", (ROOT / "cockpit" / "app" / "config.py").read_text(encoding="utf-8"))

    def test_both_languages(self):
        i18n = (ROOT / "cockpit" / "static" / "i18n.js").read_text(encoding="utf-8")
        for key in ("su.ag.token", "su.tk.t", "su.tk.s", "su.tk.how"):
            self.assertEqual(i18n.count(f'"{key}"'), 2, key)


if __name__ == "__main__":
    unittest.main()
