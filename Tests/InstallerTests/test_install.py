"""Exercise installation failures against disposable apps, never the host registry."""
from contextlib import redirect_stderr
import io
import plistlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import install
from project import APP_IDENTIFIER, APP_NAME, EXTENSION_NAME, LEGACY_IDENTIFIER, LSREGISTER


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.make_app(self.root / "Build" / APP_NAME, APP_IDENTIFIER, "new")
        self.applications = self.root / "Applications"
        self.backups = self.root / "Backups"

    def make_app(self, app, identifier, marker):
        (app / "Contents/PlugIns" / EXTENSION_NAME).mkdir(parents=True)
        with (app / "Contents/Info.plist").open("wb") as output:
            plistlib.dump({"CFBundleIdentifier": identifier}, output)
        (app / "marker").write_text(marker)
        return app

    def commands(self, failure=None):
        def invoke(*arguments):
            if arguments[0] == "ditto":
                import shutil
                shutil.copytree(arguments[1], arguments[2])
            if failure is not None:
                failure(arguments)
        return invoke

    def test_preserves_previous_app_on_success(self):
        old = self.make_app(self.applications / APP_NAME, LEGACY_IDENTIFIER, "old")
        with patch.object(install, "run", side_effect=self.commands()), patch.object(install, "wait_for_registration"):
            destination = install.install(self.source, self.applications, self.backups)
        self.assertEqual(destination, old)
        self.assertEqual((destination / "marker").read_text(), "new")
        self.assertEqual([(path / "marker").read_text() for path in self.backups.iterdir()], ["old"])

    def test_refuses_to_replace_an_unrelated_app(self):
        existing = self.make_app(self.applications / APP_NAME, "example.unrelated", "unrelated")
        with patch.object(install, "run"), self.assertRaisesRegex(RuntimeError, "another application"):
            install.install(self.source, self.applications, self.backups)
        self.assertEqual((existing / "marker").read_text(), "unrelated")
        self.assertFalse(self.backups.exists())

    def test_restores_old_app_even_when_unregister_fails(self):
        old = self.make_app(self.applications / APP_NAME, LEGACY_IDENTIFIER, "old")
        additions = 0

        def fail(arguments):
            nonlocal additions
            if arguments[:2] == ("pluginkit", "-a"):
                additions += 1
                if additions == 1:
                    raise subprocess.CalledProcessError(1, arguments)
            if arguments[:2] == (str(LSREGISTER), "-u"):
                raise subprocess.CalledProcessError(2, arguments)

        with patch.object(install, "run", side_effect=self.commands(fail)), patch.object(install, "wait_for_registration"), redirect_stderr(io.StringIO()):
            with self.assertRaises(subprocess.CalledProcessError) as raised:
                install.install(self.source, self.applications, self.backups)
        self.assertEqual(raised.exception.returncode, 1, "Preserve the original installation error")
        self.assertEqual((old / "marker").read_text(), "old")

    def test_removes_only_the_new_app_when_registration_times_out(self):
        with patch.object(install, "run", side_effect=self.commands()), patch.object(
            install, "wait_for_registration", side_effect=RuntimeError("registration timed out")
        ):
            with self.assertRaisesRegex(RuntimeError, "registration timed out"):
                install.install(self.source, self.applications, self.backups)
        self.assertFalse((self.applications / APP_NAME).exists())
        self.assertTrue(self.source.exists())

    def test_refuses_a_symlink_source(self):
        alias = self.root / "alias.app"
        alias.symlink_to(self.source, target_is_directory=True)
        with patch.object(install, "run") as command, self.assertRaisesRegex(RuntimeError, "Not a quicklook-typescript"):
            install.install(alias, self.applications, self.backups)
        command.assert_not_called()

    def test_registration_wait_checks_the_installed_path(self):
        extension = self.applications / APP_NAME / "Contents/PlugIns" / EXTENSION_NAME
        responses = [
            subprocess.CompletedProcess([], 0, stdout="(no matches)"),
            subprocess.CompletedProcess([], 0, stdout=f"{APP_IDENTIFIER}.Preview /different/app.appex"),
            subprocess.CompletedProcess([], 0, stdout=f"{APP_IDENTIFIER}.Preview {extension}"),
        ]
        with patch.object(install.subprocess, "run", side_effect=responses) as command, patch.object(install.time, "sleep"):
            install.wait_for_registration(extension)
        self.assertEqual(command.call_count, 3)


if __name__ == "__main__":
    unittest.main()
