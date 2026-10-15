# Project Vega

A Windows 11 / Python 3.13 musical controller for the Qanba Titan: three editable
Fret Sets, generated six-string guitar voicings, optional triangle preview and MIDI
output to an existing Windows port. The PC+DP profile and 8 ms gesture behavior
were verified on hardware. See [ARCHITECTURE.md](ARCHITECTURE.md) for the design.

**Qanba Titan → Vega software guitar controller → MIDI → DAW → VST/instrument.**
The Titan remains a normal game controller; Vega reads it without replacing its driver.

## Install / update and launch the desktop app

Run from the repository root in PowerShell. Create the environment once:

```powershell
py -3.13 -m venv .venv
```

Install or update desktop dependencies, then launch:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[desktop]"
.\.venv\Scripts\python.exe -m vega.app
```

Set the Titan's physical switches to **PC + DP**, release the buttons, and
center the lever before connecting. Vega stays open if the controller is
missing or unplugged and resumes when it reconnects. If several controllers
make selection ambiguous, launch with `--device-index N` using the index
shown in the waiting status. Run only one Vega app/diagnostic at a time.

## Playing Vega Guitar

- **Fret Sets:** Previous/Next cycle Set 1 → 2 → 3 → 1; the active set is saved.
  Button labels show their configured frets. Set changes wait until all held faces
  are released and a pending stroke has finalized; they never reinterpret a held chord.
- **Options advances the Fret Set:** its verified PC+DP mapping is pygame
  button 7, translated to symbolic OPTIONS. Each press advances once; release
  does not advance. Previous/Next remain available in the GUI. Options is
  silent and follows the same safe queue behavior as the GUI controls.
- **No held frets:** the open guitar E2 A2 D3 G3 B3 E4.
- **Held frets:** pitches are low E + fret. The lowest anchors the root; Vega
  recognizes common interval sets and keeps other combinations as Custom.
  Factory Set 1 frets **1, 5, 8** give F major (hold physical faces 1, 5 and 8).
  Any eight frets from 1–24 can be assigned to a set, including wide chord intervals.
- **RIGHT:** low string→high string. **LEFT:** high string→low string.
- **DOWN + horizontal:** FULL, all available strings, normally six, velocity 110.
  **Vertical center + horizontal:** NORMAL, highest four, velocity 90.
  **UP + horizontal:** STRICT, highest three, velocity 72. Vertical-only movement
  does not sound. Return horizontally to center before the next stroke.
- Fret/set changes are silent. Only a finalized strum triggers preview/MIDI.

### Edit Fret Sets

| Set | Factory name | FACE_1 through FACE_8 |
| --- | --- | --- |
| 1 | Chromatic | 1, 2, 3, 4, 5, 6, 7, 8 |
| 2 | Major / Dominant | 2, 4, 5, 7, 9, 10, 11, 12 |
| 3 | Minor / Blues | 2, 3, 5, 6, 7, 8, 10, 12 |

**Edit Fret Sets...** opens three tabs. Name each set (up to 40 characters) and
assign eight frets using the 1–24 controls. Names are labels, **not musical modes**.
Duplicate assignments are allowed: two buttons mapped to fret 5 remain separately
lit but select that fret only once musically. No buttons always means open guitar;
fret 0 is not an editable mapping. Blank names become “Set N”.

Save applies all three sets together, updates labels immediately and affects the
next acquired stroke. A stroke already settling keeps its original immutable
mapping. Cancel discards edits. Reset This Set / Reset All Sets are staged until
Save, and neither editing nor resetting makes sound.

The panel shows held frets, harmony, virtual-string pitches/frets and the last
stroke. Guitar voicing uses a deterministic compact-fret search, not a chord
lookup table. It may mute strings for difficult custom sets.

**Gesture settle** (default 8 ms, range 0–20) recognizes diagonal input.
**String spread** (default 10 ms, range 1–30) separates musical string onsets.
They are independent. Settle changes affect a pending gesture's next flush.
Spread changes affect subsequent strums, not already scheduled notes.

Preview **starts muted every launch** and now plays the actual voicing pitches,
coverage, velocity and offsets used by MIDI. Unmute to audition triangle tones;
it is not a sampled guitar. Startup prebuilds the tones, so allow a few seconds.
Three strums can overlap; the oldest is replaced when full. Volume defaults to
65%. Mute affects preview only. Panic / Stop stops both outputs; later strums
can sound again. Audio failure leaves visualization and MIDI working.

Settle, spread, preview volume, Fret Sets, active set, MIDI selection/channel and
window geometry save under `%LOCALAPPDATA%\ProjectVega\settings.json`.
Old settings receive factory mappings automatically; malformed mappings fall
back as a complete configuration without losing unrelated valid preferences.
Preview permission is never restored. The window restores/clamps geometry,
stacks panels when narrow and scrolls when short; maximizing is not required.

## MIDI connection and FL Studio test

Vega connects to an **existing MIDI output**. It does not create a native Windows
virtual MIDI device. For a DAW on the same computer, first install/enable an
appropriate MIDI loopback cable and create a port, for example **Vega Guitar**.
The cable must expose both a Windows MIDI output for Vega and input for the DAW.
A hardware MIDI port is also usable with appropriate external routing.

1. Start the cable before Vega and your DAW; keep the cable running.
2. In Vega's **MIDI output**, click **Refresh**, then choose **Vega Guitar**
   (or the exact cable output name). Confirm **Connected**. Leave **Channel 1**.
   Selecting a port does not play a test note or change the instrument.
3. In FL Studio, open **Options → MIDI settings** (F10). In **Input**, select
   the matching cable, click **Enable**, and use **(generic controller)**.
4. Load/select an instrument channel in the Channel Rack. Keep Vega preview
   muted to hear only the DAW. With no frets held, strum down-right: the DAW
   should receive six staggered open-string notes, then note-offs. Try left,
   NORMAL, STRICT and factory Set 1 frets 1/5/8 (F major).
5. Record notes if desired and inspect their spacing in the Piano Roll. Test
   repeated strokes, **Panic**, and unplugging the Titan; notes should stop.
   Do not route FL Studio's output back into the same cable (feedback loop).

FL Studio's generic input and selected-instrument behavior are described in
its [MIDI settings](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_midi.htm)
and [Channel Rack documentation](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/channelrack.htm).
Other DAWs use the same MIDI notes; Vega has no FL-specific code. DAWs may label
octaves differently; compare MIDI numbers (open tuning 40,45,50,55,59,64).

At startup, Vega prefers the exact output name **Vega Guitar**, otherwise your
saved port. It never chooses an arbitrary system synth. A missing saved port
stays disconnected. Explicitly choosing “Not connected” disconnects this session.

**Troubleshooting:** No ports is not a fatal error. Create/enable the cable,
then Refresh and select it. **Refresh stops MIDI notes, rescans and reconnects
the same selected port if available**. Windows output inventory is checked at
most once every two seconds while connected; a detected inventory change causes
the same safe rescan. Failed/disappeared ports stay disconnected until Refresh
or selection. Some drivers conceal topology changes; Refresh remains the recovery
control. MIDI errors do not disable preview. Windows driver loss
can prevent note-offs reaching the DAW; use its panic command if needed.
Microsoft MIDI Mapper / GS Wavetable Synth are system synth outputs, not a
loopback cable feeding FL Studio. Run only one Vega app/diagnostic at a time.

Both Panic buttons stop preview, pending strokes and MIDI scheduling, send tracked
note-offs plus sustain-off/All Notes Off/All Sound Off, and are safe to repeat.
Channel changes stop existing MIDI notes. Default note durations are FULL 800 ms,
NORMAL 600 ms, STRICT 350 ms, defined together with velocities in `music/plan.py`.
Repeated pitches use generation tokens so an older note-off cannot stop a newer
stroke. Timing is best-effort Windows scheduling, not hard realtime.

**Native endpoint case:** not implemented in this release. No “Vega Guitar” device
is created by Vega itself, even on Windows with MIDI Services installed. See the
[release report](docs/RELEASE_INTEGRATION.md) for the SDK investigation. The external
loopback workflow above is the supported case, without dependence on any particular
cable product. The FL Studio steps are intended setup based on its documentation,
not a claim of completed live DAW testing. Ableton Live, REAPER, Cubase, Studio One
and Bitwig use ordinary MIDI input → monitored/armed instrument track routing;
select the matching cable input and channel in that host.

Mido encodes messages. On Python 3.13 the default transport is pygame's bundled
PortMidi. The released `python-rtmidi 1.5.8` has no Windows Python 3.13 wheel;
`.[rtmidi]` is optional and requires a compatible C++ build environment here.
If installed, Vega uses it automatically. Normal `.[desktop]` installation
requires no compiler. See [published RtMidi files](https://pypi.org/project/python-rtmidi/)
and [pygame MIDI](https://www.pygame.org/docs/ref/midi.html).

## Windows application and classic installer

The editable development launch above still works. To build a console-free
Windows application, install the separate build tools once, then build:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[desktop,packaging]"
.\scripts\build-windows.ps1
.\scripts\build-installer.ps1
```

Output: `dist\Vega\Vega.exe`. Keep the entire `dist\Vega` folder together;
its `_internal` directory contains Qt, SDL, Python, and the application data.
No Python installation is needed to run that packaged folder. Build on
Windows using Python 3.13. Generated build outputs stay out of Git.

Install [Inno Setup 6](https://jrsoftware.org/isdl.php) for the second build step,
or pass `-Compiler C:\path\ISCC.exe`. The app build collects version-matched
third-party license notices from official upstream repositories (cached in
`build/license-cache`); first build needs network access. No build tools or
network connection are required to run the finished app.

Installer output: **`dist\installer\Vega-Setup.exe`**. It is a compact, light,
Windows-2000-style wizard with warm gray panels, Tahoma, unthemed beveled controls,
plain plum Vega artwork, and Welcome, destination, shortcut task, confirmation, progress
and completion pages. Default destination: `%LOCALAPPDATA%\Programs\Vega`.
It installs per user without requesting admin privileges. Start Menu gets **Vega**;
Desktop is an optional unchecked task. Normal launches need no Python/repository
or PowerShell. Windows Settings → Apps → Vega provides the uninstaller.

Rerunning Setup uses stable application identity `ProjectVega.Vega` and replaces
the installed application files. Close Vega first. Uninstall removes installed
files and owned shortcuts, **not** `%LOCALAPPDATA%\ProjectVega\settings.json`.
No settings-removal option is provided; remove your settings manually only if
you want a reset. Unknown files in the installation are not recursively erased.

Setup also upgrades the older developer-script installation **in place**: close
Vega, keep the default destination and install. It recognizes the legacy Vega
ownership marker, installs the current app at the root, and retargets Start Menu
and any existing legacy Desktop shortcut. Settings remain untouched. Old
`releases` folders and `install.json` are retained as recoverable backups, not
executed by the updated shortcuts, and are not deleted by the new uninstaller.
Future Setup runs upgrade the registered installation normally. Unrelated
nonempty folders/shortcuts remain protected. Legacy helpers refuse to operate
on a Setup-managed installation; use Windows Apps to uninstall it.

### Windows Sandbox preview

On editions with Windows Sandbox available, start a fresh Sandbox and copy only
`Vega-Setup.exe` into it (or use a read-only mapped folder). Do not map your personal
settings directory. Run Setup inside Sandbox, try Desktop unchecked and checked,
launch Vega, edit/save a Fret Set, reinstall the same installer, and verify that
the edit survives. Uninstall through Windows Apps; confirm shortcuts/files are
gone while `%LOCALAPPDATA%\ProjectVega\settings.json` remains. Closing Sandbox
discards its changes. Hardware passthrough/real Titan input is a separate host test.
Windows Home may not offer Sandbox; do not enable unsupported workarounds.

The app and installer are **unsigned development builds**; SmartScreen may warn.
No signing or security-bypass mechanism is included.

### Legacy developer copy/install helpers

Install per user and create **Vega** desktop and Start Menu shortcuts:

```powershell
.\scripts\install-local.ps1
```

Or use `.\scripts\install-local.ps1 -Build` to build first. Normal use is then
double-clicking **Vega**, with no terminal. The shortcuts launch `Vega.exe`
directly and use its icon. Installation lives beneath
`%LOCALAPPDATA%\Programs\Vega\releases\<build-hash>`; updates get separate
folders so Qt/SDL DLLs cannot mix across builds. Close the installed Vega
before updating. Previous builds remain until uninstall. A build already
installed is reported rather than overwritten.

Remove the installed copies and matching shortcuts:

```powershell
.\scripts\uninstall-local.ps1
```

Uninstall removes only manifest-listed app files and matching Vega shortcuts.
It preserves `%LOCALAPPDATA%\ProjectVega` settings and unlisted files. No admin
rights, system-wide settings, updater, or installer framework are involved.

The original claw-and-six-strings icon has **no star or lettering**. Its SVG
source and seven-size ICO live in `src/vega/app/resources/`. The build regenerates
the ICO and uses it for the executable and Qt window/taskbar identity. The
UI deliberately uses dated plum Aero caption strips, etched borders, gloss,
Segoe UI, and a conventional status bar without decorative taglines.

Optional build verification:

```powershell
.\scripts\smoke-windows.ps1
.\tests\test_windows_helpers.ps1
```

The smoke check starts and closes the actual executable, checks its GUI
subsystem, resources, mute state, and device status, and saves a report under
`build`. It does not change personal settings. The build is unsigned; Windows
may show its usual downloaded-app reputation prompt when shared with another PC.

In PC+DP mode, horizontal lever movement starts LEFT or RIGHT strums; the
vertical position marks them FULL (down), NORMAL (center), or STRICT (up).
Returning horizontally to x=0 rearms the next stroke even if up/down remains
held. The eight main face controls include two trigger-style axes, normalized
to ordinary symbolic presses and releases in the Titan profile.

## Inspect live gestures

With the Titan set to physical PC + DP mode, run:

```powershell
.\.venv\Scripts\python.exe -m vega.diagnostics.inspect_gestures --log gestures-8ms.txt
```

The diagnostic shows symbolic FACE and lever changes and prints each finalized
`STRUM` with its LEFT/RIGHT direction, FULL (down)/NORMAL (vertical center)/
STRICT (up) character, and held fingering at the stroke. Its startup checklist
covers fast horizontal strokes, upper and lower arcs, quarter circles, and
fingering snapshots. Close the small window or press Ctrl+C to stop. If more
than one controller is connected and the Titan cannot be identified by name,
use `--device-index N` from the displayed choices.

The default 8 ms diagonal settle window is experimental. Compare it on the
real Titan using `--settle-ms 4`, `6`, `8`, `10`, or `12`, giving each run a
different `--log` filename. The tool never overwrites an existing log.

## Install (PowerShell, Python 3.13)

Run these from the repository root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

## Record a session

Set the Titan's physical lever switch to DP, then run:

```powershell
.\.venv\Scripts\python.exe -m vega.diagnostics.inspect_titan --mode DP --log titan-dp.txt
```

Repeat with `--mode LS --log titan-ls.txt` and `--mode RS --log titan-rs.txt`.
The tool prints the full checklist at startup. Close its small window or press
Ctrl+C in the terminal to finish. The log file must not already exist; this
protects a previous capture. The log contains elapsed and `perf_counter()`
timestamps, device metadata, baseline state, and changed events. No physical
button mapping is assumed.

If the Titan exposes an axis for the lever, its raw float values may vary or
drift. The inspector logs every changed value; `NEGATIVE`, `ZERO`, and
`POSITIVE` are sign labels, not presumed UP/DOWN/LEFT/RIGHT. Hat tuples are
shown with direction names. The session mode is the setting you supplied,
because SDL cannot read the physical switch position.

For future mode mapping, the useful log parts are `SESSION` and `INITIAL`
(device identity/counts), `BASELINE`, the changed `BUTTON`/`HAT`/`AXIS` lines,
and `CONNECTED`/`DISCONNECTED` lines. Record the physical test order and any
controls with no events alongside the log. PC+DP is already mapped from the
verified observations in [ARCHITECTURE.md](ARCHITECTURE.md).

## Run tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## License

Project Vega uses the [Unlicense](LICENSE). Setup has no restrictive EULA or
acceptance page. Third-party components retain their own licenses; the packaged
distribution includes [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and a
`licenses` directory. Release verification and known limitations are recorded
in [docs/RELEASE_INTEGRATION.md](docs/RELEASE_INTEGRATION.md).
