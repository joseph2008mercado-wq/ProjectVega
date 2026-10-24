# Clean Windows acceptance — developer checklist

This is release testing, **not an end-user prerequisite**. The project owner
reported that the v1.0.0 installer with SHA-256
`5749330e702f389a67958b8960de29d7e380dcded5a05c8136d2701616051105`
passed on another Windows environment on 2026-10-24. Screenshots and exact OS
build were not supplied. Use this checklist again for future builds.

Use a clean Windows 11 x64 PC, Sandbox or disposable VM without Python, Git, Inno
Setup, build tools, Vega source, MIDI cable, DAW or VST. Use Sandbox only where
officially supported; do not bypass edition/admin restrictions. Do not map your
personal settings into the guest.

1. Copy **only Vega-Setup.exe** into the guest. Leave the repository and `dist/Vega`
   on the host. Disconnect guest networking if practical; Setup is offline.
2. Double-click Setup. Confirm no prerequisite prompts, downloads or compilation.
   Record any unsigned-app warning normally; do not disable Windows security.
3. Check classic light/Tahoma/warm-gray wizard, plum claw/string art, no star/EULA.
   Walk Welcome → Destination → Additional Tasks → Ready → Progress → Finished.
   Check readability and navigation at 100%, 125%, 150% scaling.
4. Install to `%LOCALAPPDATA%\Programs\Vega` without elevation. Leave Desktop
   unchecked. Confirm Start Menu Vega exists and Desktop Vega does not.
5. Launch from **Start Menu**, not PowerShell. Confirm no console, real icon,
   GUI, muted preview, no Titan and no loopback/DAW. No MIDI outputs or disconnected
   system outputs is normal. Missing audio must not block the GUI.
6. Open Edit Fret Sets. Save a recognizable name and fret. Change active set,
   volume/timing/window size, then close. Check the saved JSON at
   `%LOCALAPPDATA%\ProjectVega\settings.json`.
7. Create an unrelated `keep.txt` inside the install folder and retain its contents.
8. Rerun Setup with Desktop checked. Confirm one registered Vega install, both
   shortcuts targeting root `Vega.exe`, not a hashed releases folder.
9. Launch from Desktop. Confirm custom settings survived, but preview is muted.
   Resize to a small window; scroll to MIDI controls. Close/reopen once more.
10. Uninstall via Windows Settings → Apps → Vega (or the installed uninstaller).
    Confirm owned app files, shortcuts and registration are gone, while custom
    settings and `keep.txt` remain unchanged.
11. Reinstall and confirm the saved settings load again. Close and uninstall.
12. Record results, then discard the disposable guest if used. Never overwrite
    another PC's settings with test data.

Send back the installer SHA-256, Windows edition/build, pass/fail for steps 1–12,
and screenshots or exact text of any failure. Specifically confirm that custom
settings and `keep.txt` survived reinstall/uninstall. If Windows Application
Control blocks Setup, Vega or uninstall, report which executable and the message;
do not disable security policy. This build PC blocked the unsigned test uninstaller;
the owner reports that uninstall passed on the other environment.

For previous-version upgrade testing, install the preceding official Setup first,
save settings, then install the v1.0.0 release. Both must use `ProjectVega.Vega`.
`scripts/test-installer.ps1` separately exercises synthetic legacy migration,
unsafe manifests and unknown-file protection with an isolated test identity.

## Physical checks outside Sandbox

- Final packaged build: eight faces, Options once/release/queued switching,
  LEFT/RIGHT, upper STRICT/lower FULL rocking, neutral rearming, diagonal settle,
  pending-stroke editing, unplug/reconnect and audible preview.
- Real loopback + FL Studio/VST: open/F-major notes, recorded spacing, rapid
  equal-pitch retriggers, channel/port changes, repeated Panic, port loss, Titan
  unplug and closing Vega during active notes.
- Fake-clock tests do not measure end-to-end audio/MIDI latency.

Current result: [RELEASE_INTEGRATION.md](RELEASE_INTEGRATION.md).
