"""The setup assistant writes .env values that docker compose, setup.sh and Python all read back unchanged."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cockpit" / "app"))
import configure  # noqa: E402


class EnvValues(unittest.TestCase):
    def write(self, values):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            with mock.patch.object(configure, "ENVF", env):
                configure.env_set(values)
                return env.read_text(encoding="utf-8"), configure.env_read()

    def test_special_characters_round_trip(self):
        text, back = self.write({"VCENTER_PASSWORD": "pa$$ #1 \"x\""})
        self.assertIn("VCENTER_PASSWORD='pa$$ #1 \"x\"'", text)
        self.assertEqual(back["VCENTER_PASSWORD"], 'pa$$ #1 "x"')

    def test_values_that_cannot_be_stored_unchanged_are_refused(self):
        # an apostrophe used to vanish silently; a trailing backslash broke the whole .env for docker compose
        for bad in ("it's", "C:\\temp #1\\", "two\nlines", "tab\there"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.write({"VCENTER_PASSWORD": bad})

    def test_assistant_asks_again_instead_of_storing_a_wrong_password(self):
        ask = configure.Ask("en", True)
        with mock.patch.object(configure.getpass, "getpass", side_effect=["it's", "fine$pass"]), \
             mock.patch("builtins.print"):
            self.assertEqual(ask.secret("vcp"), "fine$pass")


if __name__ == "__main__":
    unittest.main()
