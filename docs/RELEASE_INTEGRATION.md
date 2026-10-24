# Vega v1.0.0 release verification

Stabilization date: **2026-10-15**. Base: `d8a4a882fd5c0fe700a53a0303778b6bc6a83a72`.
Version metadata is 1.0.0. The tested installer was published on 2026-10-24 as
[v1.0.0](https://github.com/tamarin08/ProjectVega/releases/tag/v1.0.0), tagged at
`ca6bd1353929f4205df5897c6835a1b7d7446f90`. GitHub confirms the uploaded
34,914,063-byte installer has SHA-256
`5749330e702f389a67958b8960de29d7e380dcded5a05c8136d2701616051105`.

**Release acceptance:** on 2026-10-24 the project owner reported that this exact
installer passed the clean Windows install/reinstall/uninstall checklist and the
packaged Titan and FL Studio checks. The owner did not supply screenshots, Windows
build details or individual measurements; those results are recorded as
user-reported, not independently reproduced on this build PC. See the
[clean Windows checklist](CLEAN_WINDOWS_TEST.md) and host evidence below.

## Final pass report

1. **Architecture issues found:** two competing installation systems, stale
   arithmetic-bank/developer-install documentation, duplicate runtime close,
   post-close polling, overflow in numeric settings conversion, stale SDL recovery
   state, retained preview PCM, and native Qt objects surviving test teardown.
2. **Changes:** one Setup installation path; isolated one-time legacy cleanup;
   idempotent shutdown; no polling after close; resource reset/recovery; field-local
   settings fallback; explicit Qt deletion; build inventory validation. No framework
   or wholesale rewrite. Runtime input/music/output boundaries remain separate.
3. **Behavior unchanged:** verified PC+DP IDs including Options=7; symbolic faces;
   factory/custom Fret Sets and queued switching; harmony, deterministic voicing,
   open tuning; LEFT/RIGHT; FULL/NORMAL/STRICT; settle/rearm; shared StrumPlan;
   spread, velocities/durations; muted-start preview; MIDI selection/channel/Panic;
   Aero appearance, responsive layouts, icon and settings compatibility.
4. **Removed:** legacy install/uninstall/common scripts and their dedicated
   PowerShell test; obsolete `MUSIC_ENGINE_IMPLEMENTATION.md`. Git retains history.
   Useful Titan/gesture diagnostics remain. Internal `bank` names are set indexes,
   not a second abandoned music engine, so they were not renamed for style.
5. **Dependencies:** runtime constraints unchanged. Core pygame; desktop Qt/Mido;
   optional RtMidi; packaging PyInstaller; unittest is standard library. Inno is
   build-only. No new runtime dependency, compiler, download or service.
6. **Reliability/performance:** regression tests demonstrated overflow and shutdown
   defects. Native test processes intermittently crashed after passing assertions;
   Windows crash records identified Qt6Core during teardown. Explicit window/
   deferred-dialog release eliminated this in repeated runs. No timing algorithm
   was optimized without evidence. No worker threads or per-note timers added.
7. **MIDI reliability:** existing token/heap design retained. Added stress and failure
   checks for 2,000 rapid overlapping strums, paired on/off messages, port switches,
   partial panic failure, close failure, disconnect and repeated lifecycle cleanup.
   Empty inventory now says “No MIDI outputs available”, not “install a cable first”.
8. **Controller reliability:** SDL pump failure releases the stale handle, backs off
   two seconds and announces reconnection. Close clears the handle before releasing
   it. Mapping and gesture recognizer are unchanged. Shutdown resets pending state.
9. **GUI/window:** layout, paint, fonts, editor and geometry policy are unchanged.
   Closing saves once, stops all timers and releases native windows before Python
   teardown. Test teardown drains deferred widgets. Hidden packaging smoke flags
   exercise the real editor with an explicitly isolated settings file.
10. **Previous installer architecture:** hashed releases plus a manifest-managed
    PowerShell installer/uninstaller, alongside Inno Setup. Both looked like
    supported installation paths and legacy copies accumulated.
11. **Final installer architecture:** Inno Setup copies the one complete PyInstaller
    output, owns shortcuts/registration/uninstall, supports reinstall and migration.
    No package/version manager, updater, secondary build or settings database.
12. **`install-local.ps1`:** removed, not retained as an alternate install path.
13. **`uninstall-local.ps1`:** removed; uninstall through Windows Apps/Setup's uninstaller.
14. **Legacy migration:** after successful Setup, bundled Vega's packaging-only
    maintenance entry validates exact JSON schema/owner, complete inventory,
    path boundaries and executable hashes. It never initializes musical runtime.
    It deletes only listed files and empty known directories. Failures preserve
    uncertain files and are noted in the Setup log; the new app can still launch.
15. **Old `releases/<hash>`:** removed when safely proven and empty after owned-file
    removal. A directory containing unknown files remains. Malformed manifests,
    changed executables, locks or redirected paths are not force-cleaned. Completed
    old metadata is removed; no intentional rolling backup/version store remains.
16. **Unknown-file protection:** no recursive tree deletion. Validate the complete
    manifest before deletion; reject traversal, absolute paths, alternate streams,
    reserved names, duplicate entries/keys and junctions/symlinks. Unlisted files
    survive. Setup rejects unrelated nonempty folders, foreign shortcuts and
    legacy root collisions with new payload paths. Ordinary uninstall uses Inno's log.
17. **Settings:** `%LOCALAPPDATA%\ProjectVega\settings.json` is never Setup-owned.
    Upgrade/uninstall preserve it. Invalid numeric fields fall back independently;
    invalid mapping tuples default atomically. Other valid/unknown preferences survive.
18. **Technology:** PyInstaller one-folder, Inno Setup 6 classic wizard; no MSIX/driver.
19. **Style:** intentionally Windows 2000/XP/early Vista, warm gray, Tahoma, beveled
    controls, plum Vega claw/string artwork, no star/EULA/marketing redesign.
20. **Developer commands:** create Python 3.13 `.venv`, install `.[desktop,packaging]`,
    install Inno Setup on the build PC; then `scripts/build-windows.ps1` followed
    by `scripts/build-installer.ps1`. Develop with `python -m vega.app` in that env.
21. **Installer artifact:** `dist/installer/Vega-Setup.exe` (generated, not Git-tracked).
22. **Default destination:** `%LOCALAPPDATA%\Programs\Vega`, per user, no elevation.
23. **Shortcuts:** Start Menu Vega, optional unchecked Desktop Vega. Existing owned
    legacy Desktop link is retargeted. Links launch root Vega.exe directly.
24. **Upgrade:** stable `ProjectVega.Vega` identity; same destination and registration.
    Reinstall replaces owned app files, preserves settings; no “Vega 2/New” directory.
25. **Uninstall:** removes Setup-owned files/shortcuts/registration; preserves settings
    and unknown files. No “delete settings” action or recursive cleanup.
26. **Zero developer prerequisites:** finished Setup consumes only bundled payload.
    No pip, venv, Git, repository, compiler, source download or packaging step is
    executed on the user's PC. The owner reports successful clean Windows testing.
27. **Python:** bundled Python 3.13 runtime; no end-user Python installation required.
28. **Inno Setup:** build-machine compiler only; end users run the finished EXE.
29. **Build tools:** not needed by installed Vega. Python/Qt/SDL/PortMidi and required
    VC runtime DLLs are bundled. A build-time inventory rejects incomplete payloads.
30. **MIDI loopback:** optional post-install setup for same-PC DAW routing only.
    No loopback, MIDI ports, DAW, VST or Titan is required to launch/edit settings.
31. **Clean Windows result:** unavailable on this build PC: WindowsSandbox.exe and
    checked VM tools/services were absent. The owner reports all checks passed on
    another Windows environment using the exact published installer, including
    uninstall and settings/unknown-file preservation. No screenshots or OS build
    details were supplied. Host reduced-PATH checks are separate evidence.
32. **Licenses:** Unlicense unchanged; no EULA. Versioned upstream/installed third-party
    notices and sources inventory included. Qt/SDL remain replaceable dynamic
    libraries. Unused Qt PDF/Virtual Keyboard/QML payload remains excluded.
    Exact dependency/source redistribution obligations still need release review.
33. **Unit tests:** baseline 106 passed before edits; final 124 passed, exit 0,
    including three additional consecutive full runs after final source edits.
34. **MIDI stress:** 2,000 strums at injected 5 ms intervals, no sleeps. Tests check
    each pitch balance stays 0/1, eventual complete release, empty queue/active map,
    and queue bounded by scheduling horizon rather than session length. This is
    correctness coverage, not a hardware latency benchmark.
35. **Qt:** window/editor tests cover small-window scroll access, layout/DPI policy,
    settings, silent editing and shutdown. Five tests passed at each of 125% and
    150% scaling, with clean process exit.
36. **Packaged smoke:** checks frozen native Qt GUI, icon, no console, muted preview,
    no selected controller, editor and persisted settings. Dummy audio prevents
    unintended sound; it is not audible preview validation. Results below.
37. **Installer checks:** compilation, GUID-isolated fresh/reinstall, Desktop off/on,
    registration and installed editor/settings persistence passed. Separate Setup
    runs verified legacy cleanup and unsafe-manifest preservation. The complete
    installer matrix did not finish: Windows policy blocked the test uninstaller.
    This host's uninstall and later fresh-legacy/foreign-folder scenarios remain
    unverified; the owner reports clean Windows uninstall passed elsewhere.
38. **Physical Titan:** the owner reports packaged Titan checks passed. The build
    PC did not independently repeat physical face/Options/arc/settle, reconnect or
    audible preview tests during this pass; earlier mapping tests are retained.
39. **Live FL Studio:** the owner reports the DAW checks passed. No recording,
    timing measurements or screenshots were supplied for independent review.
40. **Known v1 limits:** PC+DP only, no native virtual endpoint, no hard realtime,
    heuristic voicing, triangle preview, same-channel equal-pitch retrigger,
    one runtime per process without single-instance enforcement, unsigned binaries.
    A vanished driver cannot be guaranteed to receive note-offs; use DAW Panic.
41. **Release outcome:** v1.0.0 was tagged and published with the exact installer
    the owner confirmed testing. Host-specific unfinished checks and lack of
    independent external test artifacts are documented here, not counted as passes.

## Verification evidence

### Completed on the build PC

- `python -m unittest discover -s tests -v`: **124 passed, exit 0**. Three further
  full runs each passed 124 with exit 0. Earlier Qt teardown diagnosis was followed
  by six consecutive clean full runs at the then-current count of 123.
- Separate `test_window.py` / `test_fret_set_editor.py` runs: **5 passed at 125%**
  and **5 passed at 150%**, all exit 0. These are automated widget checks, not a
  claim that the final wizard was visually tested at every scale.
- `scripts/build-windows.ps1`: self-contained version 1.0.0 app built successfully.
  `scripts/build-installer.ps1`: classic Inno Setup installer compiled successfully.
  Distribution SHA-256 inventory verification passed. Notices include 182 upstream
  license files plus installed dependency licenses and source/version records.
- Native dependency audit: 117 PE binaries, 901 imports, no unresolved imports
  against the bundle, this host's System32 and Windows API sets. This static check
  does not establish availability on a clean guest.
- Final packaged smoke: native Windows Qt, real icon, no console, muted startup,
  missing Titan handled, no MIDI cable needed, clean exit. Windows-only PATH and
  cleared Python environment were used. The failure-injected audio run also
  launched and exited successfully, reporting audio unavailable without blocking
  the GUI. Reports: `build/smoke-c1ad1644a21f4cfaadd0054a447c5322.json` and
  `build/smoke-41b46cb773db4cc4ac25605fa9358c27.json`. Dummy audio was used for
  the first run; neither run proves audible preview operation.
- Isolated installer evidence is under
  `build/installer-validation/7441dad257124ba88de922f32133f7a1/`.
  `install.log`, `upgrade.log`, `fresh-smoke.json` and `upgraded-smoke.json`
  demonstrate fresh install, per-user registration, Desktop off/on, root-targeted
  shortcuts, launch, and custom editor value/name preservation through reinstall.
- Separate `verified-cleanup.log` and `unsafe-cleanup-preserved.log` show the
  actual Setup post-install helper removing verified legacy files/metadata,
  preserving unknown files/settings, and rejecting traversal before deletion.
  These ran in the existing managed fixture; they do not establish the entire
  fresh-legacy destination/shortcut acceptance matrix. The final additional
  hash check on legacy shortcut targets was compiled and policy-tested, not
  exercised in that interrupted end-to-end matrix.

### Build-PC limitation and owner acceptance

Windows Application Control blocked `installed/unins000.exe` in the GUID test
fixture. Code Integrity event 3077 identified an enterprise signing-policy block.
The test stopped; this is **not an uninstall pass**. Security policy was not changed
or bypassed. Only the GUID test shortcuts and registration were manually removed
after verifying their targets; fixture files/logs remain for diagnosis. The real
Vega installation and personal settings were not cleanup targets.

The owner reports successful clean Windows installation, reinstall, uninstall,
settings/unknown-file preservation, packaged Titan and FL Studio testing with the
same installer SHA-256 published above. These are user attestations; exact Windows
build, logs and measurements were not provided. The host-only synthetic
fresh-legacy/foreign-folder matrix in `scripts/test-installer.ps1` remains partially
unrun because of the build PC's policy block. The verified and unsafe migration
cases completed separately as described above. If an organization blocks the
unsigned release, follow its approved distribution/signing process rather than
disabling protection.

Generated logs, manifests, executables and test fixtures stay under ignored
`build/` and `dist/`; none are source-controlled release artifacts.

Qt ownership follows its [deferred-deletion documentation](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QObject.html#PySide6.QtCore.QObject.deleteLater)
and [posted-event cleanup API](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QCoreApplication.html#PySide6.QtCore.QCoreApplication.sendPostedEvents).
Setup's legacy recognition uses the documented
[SHA-256 file check](https://jrsoftware.org/ishelp/topic_isxfunc_getsha256offile.htm).
