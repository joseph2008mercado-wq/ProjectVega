# Vega 0.2.0 release integration

Base: `6a4d57d8e3b08d49c98f3f0e456ca947fe71f710`.
Verification date: 2026-10-14, Windows 11 25H2 build 26200.9457, Python 3.13.14.

## Delivery checklist

1. **Files:** the complete source/documentation inventory is below. Build outputs
   remain ignored; no generated executable or local settings are committed.
2. **Factory sets:** Chromatic `(1,2,3,4,5,6,7,8)`; Major / Dominant
   `(2,4,5,7,9,10,11,12)`; Minor / Blues `(2,3,5,6,7,8,10,12)`.
3. **Model:** immutable `FretSet(name, frets)`, exactly eight integer slots 1–24,
   exactly three sets. Factory defaults are defined once in `music/fret_sets.py`.
4. **Resolution:** symbolic FACE indexes the active mapping before `FretSelection`.
   No raw controller IDs or preset-name special cases enter harmony/voicing.
5. **Duplicates:** sorted/deduplicated musical frets; independent physical held
   faces remain visible. No held faces preserves exact open tuning 40/45/50/55/59/64.
6. **Options:** existing verified button 7 → OPTIONS remains untouched. Rising
   edges cycle 1→2→3→1; releases/unchanged repeats never advance or make music.
7. **Safe switching:** existing queue waits for released faces and no pending
   stroke. GUI Previous/Next share the runtime API. Pending strokes additionally
   retain the immutable mapping they acquired, protecting them from editor Save.
8. **Editor:** three Qt tabs, name limit 40, trimmed/blank-name fallback “Set N”,
   eight range-controlled spin boxes per tab, Save/Cancel and staged resets.
   Save changes the entire mapping tuple atomically and immediately refreshes
   labels; the next newly acquired stroke uses it. Non-blocking window modality
   allows input/output timers to continue. Dialog contrast was visually corrected.
9. **Persistence:** existing JSON store now saves sets, active index, MIDI selection/
   channel and Qt geometry alongside prior timing/volume. Missing/malformed mapping
   data defaults atomically. Unknown preferences are retained; mute permission
   is deliberately discarded. Geometry is restored and clamped.
10. **Harmony:** same low-E-relative pitches, lowest root and interval recognition.
    Custom mappings can include wider chord spans; names are descriptive only.
11. **Voicing:** unchanged deterministic six-string beam search and open tuning.
12. **Preview:** unchanged shared-plan triangle renderer, starts muted, same
    notes/velocities/offsets/durations as MIDI. Edits/switches/resets are silent.
13. **MIDI architecture:** one tick-driven deadline heap below `StrumPlan`;
    injected ports/open/send/close transport, no GUI-thread sleeps or per-note threads.
14. **Backends:** Mido message encoding with pygame/PortMidi in the tested Python
    3.13 build; optional Mido/RtMidi if importable. Missing/broken RtMidi import
    falls back to PortMidi. No forced C++ build and no DAW-specific messages.
15. **Native virtual endpoint:** **not implemented**. The service and virtual
    transport exist on this PC, but no App SDK runtime/tools or verified Python
    host integration were found in the inspected standard locations/registry.
    A running service alone does not establish endpoint-hosting capability.
16. **Fallback:** create/enable an external Windows loopback port, preferably
    named “Vega Guitar”; select its output in Vega and matching input in the DAW.
    Vega does not install a cable product or claim to publish a device.
17. **Ports/errors:** startup prefers exact “Vega Guitar”, then saved selection,
    never an arbitrary system synth. Explicit Refresh panics/closes/rescans and
    reconnects the same port. A two-second read-only WinMM inventory check notices
    changes behind PortMidi's cache and requests the same safe rescan. Failed or
    missing ports clear notes/queues and leave preview/input running; explicit
    Refresh retries the remembered choice. Some drivers may conceal topology changes.
18. **Ownership:** `(channel,pitch)` generation tokens; retrigger sends off then
    on, and old note-offs cannot terminate a newer generation. Identical pitches
    on one channel retrigger rather than representing independent string voices.
19. **Panic:** both GUI Panic controls stop preview, pending gesture and scheduled
    MIDI, explicit active note-offs and CC64/123/120 across all 16 channels.
    Repeated Panic is safe and does not rearm a still-held lever. Shutdown cleans up.
20. **FL Studio:** start the external cable; select its output in Vega, channel 1;
    FL Studio F10 → MIDI Input → matching cable → Enable → generic controller;
    select an instrument channel, keep Vega preview muted and strum. This is
    documented intended setup, not a completed end-to-end FL Studio test here.
21. **Other DAWs:** ordinary MIDI 1.0 Note On/Off, channels 1–16 and velocities.
    Select the cable input on a monitored/armed instrument track in Ableton,
    REAPER, Cubase, Studio One, Bitwig or another conventional MIDI host.
22. **Installer:** Inno Setup 6.7.3; real standalone `Vega-Setup.exe`.
23. **Why:** mature per-user setup, upgrade/uninstall log and ordinary Win32 wizard;
    no custom Python installer framework. Compiler downloaded from the official
    release, SHA-256 checked against release metadata and Authenticode verified
    as Pyrsys B.V.; used in portable mode in ignored `build/tools/inno`.
24. **Style:** classic compact Windows-2000-oriented wizard, warm gray surfaces,
    Tahoma 8, unthemed/beveled child controls, simple plum Vega bitmaps. Real icon,
    no star, no marketing page. Per-window styling does not modify Windows theme.
    First classic version was visually inspected; subsequent stronger retro
    revision compiled/ran in installer tests, but its final visual inspection was
    stopped by the user's Escape key. Final aesthetic approval remains manual.
25. **Build:** `scripts/build-windows.ps1`, then `scripts/build-installer.ps1`.
    Optional `-Compiler C:\path\ISCC.exe`; first license collection needs network.
26. **Installer artifact:** `dist/installer/Vega-Setup.exe`.
27. **Install path:** `%LOCALAPPDATA%\Programs\Vega`, per user, no admin request.
28. **Shortcuts:** one Start Menu “Vega”; optional unchecked Desktop task. An
    existing legacy Vega Desktop shortcut is preserved/retargeted on migration.
29. **Upgrades:** stable AppId `ProjectVega.Vega`, executable/Setup version 0.2.0.
    Earlier manifest-based Vega installations are accepted in place: the current
    root app and same-installation shortcuts replace their active entry points.
    Unrelated nonempty folders and foreign shortcuts remain protected.
30. **Uninstall:** Windows Apps entry removes Setup-owned files and shortcuts.
    Legacy `releases` directories/manifest are retained as recoverable backups;
    they are not executed by updated shortcuts and are not recursively deleted.
31. **Settings:** outside the application directory, preserved on upgrade and
    uninstall. No destructive “remove settings” checkbox. Legacy helper scripts
    refuse a Setup-managed installation to prevent conflicting file ownership.
32. **Unlicense:** repository LICENSE verified, distributed unchanged; no EULA
    acceptance. Third-party notices and versioned source links are collected under
    `licenses`. Unused Qt PDF/Virtual Keyboard plugins and QML DLLs are excluded.
    Public redistribution still requires checking the exact dependency/source
    obligations for the release; Vega's Unlicense does not replace those licenses.
33. **Sandbox:** README describes copying only Setup into a disposable Windows
    Sandbox, testing shortcut choices/reinstall/settings/uninstall, then closing
    it. Sandbox was not available in the checked host tooling; isolated identity
    testing was used instead. No unsupported Windows Home workaround was attempted.
34. **Automated tests:** **106 passed, zero failures/skips**. Qt window (3) and
    editor (2) tests also passed in separate processes at 125% and 150% scale.
    Legacy PowerShell path/ownership checks passed. `git diff --check` passed.
    Tests use fake controller/audio/MIDI and injected times, no arbitrary sleeps.
35. **Packaged smoke:** passed with native Windows Qt at 150% DPI, frozen Python,
    icon present, no console, preview muted, actual connected Qanba Titan detected,
    correct three factory sets/open tuning/channel 1. Enumerated Microsoft MIDI
    Mapper and GS Wavetable Synth without auto-connecting. Used dummy audio driver;
    it is a startup check, not an audible/DAW timing test.
36. **Installer validation:** production Setup built successfully. The same script
    and payload were compiled with GUID-isolated AppId/destination/shortcut names.
    Passed fresh install, Desktop off, upgrade with Desktop on, installed startup
    with developer Python removed from PATH, uninstall, legacy-layout in-place
    migration with both shortcuts retargeted, second uninstall and backup/settings
    preservation. Logs confirm non-administrative mode and HKCU uninstall entry.
    Actual personal settings hash remained unchanged. Test app files/shortcuts
    were removed; ignored logs/setup files and synthetic legacy backups remain.
37. **Manual verification remaining:** final retro appearance approval; physical
    Options/face/arc performance against the final build; audible preview; actual
    loopback hotplug and DAW/VST recordings/retrigger/panic; performance under load;
    different machines/screens; a full Windows Sandbox install. The real installed
    Vega copy was not modified by these isolated tests.
38. **Known limitations:** no native endpoint, no code signing, no hard realtime,
    same-channel equal-pitch retrigger, heuristic voicing, one desktop runtime per
    process, retained legacy backups, no automatic updater. Drivers that vanish
    cannot be guaranteed to receive final note-offs; use the DAW's Panic if needed.

## Evidence and references

Final packaged startup: `build/smoke-9264b2a259f348f19ecf2abb9e5da3a0.json`.
Full final installer validation:
`build/installer-validation/3a8dbf4bf6fd49d5931c1107320a9877/`.
Qt renders: `build/release-window.png`, `build/release-editor-fixed.png`.
Artifacts/evidence are local and ignored, not committed or uploaded as a release.

Microsoft documents that app-hosted virtual endpoints require its new MIDI SDK
and an UMP-aware host; endpoint lifetime follows the host connection. See
[Virtual Device App](https://microsoft.github.io/MIDI/kb/virtual-device-app/) and
[Virtual transport API](https://microsoft.github.io/MIDI/sdk-reference/Transports/Virtual/).
The existing WinMM-compatible transport remains below the musical plan; a future
tested native bridge can replace it without changing fingering or strumming.

The read-only inventory check follows
[midiOutGetDevCapsW](https://learn.microsoft.com/en-us/windows/win32/api/mmeapi/nf-mmeapi-midioutgetdevcapsw).
FL Studio routing follows its
[official MIDI settings documentation](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_midi.htm).
Setup uses Inno's [classic wizard](https://jrsoftware.org/ishelp/topic_setup_wizardstyle.htm)
and [lowest privileges mode](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm).

## Complete changed/added file inventory

- `ARCHITECTURE.md`
- `README.md`
- `THIRD_PARTY_NOTICES.md` (new)
- `docs/RELEASE_INTEGRATION.md` (new)
- `packaging/Vega.spec`
- `packaging/Vega.iss` (new)
- `pyproject.toml`
- `scripts/build-windows.ps1`
- `scripts/build-installer.ps1` (new)
- `scripts/collect-licenses.py` (new)
- `scripts/generate-installer-art.py` (new)
- `scripts/test-installer.ps1` (new)
- `scripts/local-common.ps1`
- `src/vega/app/__main__.py`
- `src/vega/app/identity.py`
- `src/vega/app/smoke.py`
- `src/vega/app/style.py`
- `src/vega/app/widgets.py`
- `src/vega/app/window.py`
- `src/vega/app/fret_set_editor.py` (new)
- `src/vega/midi/output.py`
- `src/vega/midi/windows_ports.py` (new)
- `src/vega/music/harmony.py`
- `src/vega/music/strum.py`
- `src/vega/music/fret_sets.py` (new)
- `src/vega/runtime.py`
- `src/vega/settings.py`
- `tests/test_app_identity.py`
- `tests/test_midi.py`
- `tests/test_music.py`
- `tests/test_runtime.py`
- `tests/test_settings.py`
- `tests/test_window.py`
- `tests/test_fret_set_editor.py` (new)
- `tests/test_fret_sets.py` (new)
- `tests/test_installer.py` (new)

The verified Titan profile, physical input mapping, guitar voicer, strum profiles
and preview backend were not changed. The only recognizer addition is a pending-
stroke cancellation method for Panic; recognition/rearming rules are unchanged.
