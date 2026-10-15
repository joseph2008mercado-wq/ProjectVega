"""Release policy checks; no compiler, admin rights or installation required."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def test_classic_per_user_stable_identity_and_no_eula(self):
        text = (ROOT / "packaging/Vega.iss").read_text()
        for setting in ('#define AppIdentity "ProjectVega.Vega"', "PrivilegesRequired=lowest",
                        "WizardStyle=classic", "DisableWelcomePage=no", "DisableDirPage=no",
                        "DisableReadyPage=no", "Uninstallable=yes", "VersionInfoCopyright=Unlicense",
                        'DefaultDirName={localappdata}\\Programs\\{#InstallFolder}',
                        'Name: "{userprograms}\\{#ShortcutName}"', 'Tasks: desktopicon'):
            self.assertIn(setting, text)
        self.assertNotIn("LicenseFile=", text)
        self.assertNotIn("[UninstallDelete]", text)
        self.assertNotIn("settings.json", text)
        self.assertIn("ConflictingShortcut", text)
        self.assertIn("install.json", text)
        self.assertIn("Managed or Legacy", text)
        self.assertIn("LegacyShortcut", text)
        self.assertIn("KeepLegacyDesktop", text)
        self.assertIn("WizardForm.Color := $00C8D0D4", text)
        self.assertIn("SetWindowTheme", text)

    def test_build_checks_inputs_and_copies_notices(self):
        script = (ROOT / "scripts/build-installer.ps1").read_text()
        self.assertIn("THIRD_PARTY_NOTICES.md", script)
        self.assertIn("ProductVersion", script)
        self.assertIn("Inno Setup 6 compiler not found", script)
        self.assertIn("collect-licenses.py", (ROOT / "scripts/build-windows.ps1").read_text())
        self.assertIn("free and unencumbered software", (ROOT / "LICENSE").read_text())
