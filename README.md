# Project Vega

A Windows 11 / Python 3.13 musical controller for the Qanba Titan: 24-fret
banks, generated six-string guitar voicings, optional triangle preview and MIDI
output to an existing Windows port. The PC+DP profile and 8 ms gesture behavior
were verified on hardware. See [ARCHITECTURE.md](ARCHITECTURE.md) for the design.

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

- **Banks:** Previous/Next cycle 1–8, 9–16, 17–24. Every launch starts in bank 1.
  Button labels show their current frets. Bank changes wait until all held faces
  are released and a pending stroke has finalized; they never reinterpret a held chord.
- **Options is NOT mapped yet.** Its raw ID still needs hardware identification.
  Use the GUI controls now; no Options/Create/Share IDs are guessed.
- **No held frets:** the open guitar E2 A2 D3 G3 B3 E4.
- **Held frets:** pitches are low E + fret. The lowest anchors the root; Vega
  recognizes common interval sets and keeps other combinations as Custom.
  Bank 1 frets **1, 5, 8** give F major (hold physical faces 1, 5 and 8).
  Frets must be in the same bank; seventh structures are recognized by the
  engine but generally span more than the eight simultaneously available frets.
- **RIGHT:** low string→high string. **LEFT:** high string→low string.
- **DOWN + horizontal:** FULL, all available strings, normally six, velocity 110.
  **Vertical center + horizontal:** NORMAL, highest four, velocity 90.
  **UP + horizontal:** STRICT, highest three, velocity 72. Vertical-only movement
  does not sound. Return horizontally to center before the next stroke.
- Fret/bank changes are silent. Only a finalized strum triggers preview/MIDI.

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

Settle, spread and preview volume save under
`%LOCALAPPDATA%\ProjectVega\settings.json`. Mute, bank and MIDI connection are
not restored. The window fits the available desktop, stacks panels when narrow
and scrolls when short; maximizing is not required. No geometry is persisted.

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
   NORMAL, STRICT and bank 1 frets 1/5/8 (F major).
5. Record notes if desired and inspect their spacing in the Piano Roll. Test
   repeated strokes, **Panic**, and unplugging the Titan; notes should stop.
   Do not route FL Studio's output back into the same cable (feedback loop).

FL Studio's generic input and selected-instrument behavior are described in
its [MIDI settings](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/envsettings_midi.htm)
and [Channel Rack documentation](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/channelrack.htm).
Other DAWs use the same MIDI notes; Vega has no FL-specific code. DAWs may label
octaves differently; compare MIDI numbers (open tuning 40,45,50,55,59,64).

**Troubleshooting:** No ports is not a fatal error. Create/enable the cable,
then Refresh and select it. **Refresh stops/disconnects MIDI before rescanning**;
select the port again. MIDI errors do not disable preview. Windows driver loss
can prevent note-offs reaching the DAW; use its panic command if needed.
Microsoft MIDI Mapper / GS Wavetable Synth are system synth outputs, not a
loopback cable feeding FL Studio. Run only one Vega app/diagnostic at a time.

Mido encodes messages. On Python 3.13 the default transport is pygame's bundled
PortMidi. The released `python-rtmidi 1.5.8` has no Windows Python 3.13 wheel;
`.[rtmidi]` is optional and requires a compatible C++ build environment here.
If installed, Vega uses it automatically. Normal `.[desktop]` installation
requires no compiler. See [published RtMidi files](https://pypi.org/project/python-rtmidi/)
and [pygame MIDI](https://www.pygame.org/docs/ref/midi.html).

## Windows application build and shortcuts

The editable development launch above still works. To build a console-free
Windows application, install the separate build tools once, then build:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[desktop,packaging]"
.\scripts\build-windows.ps1
```

Output: `dist\Vega\Vega.exe`. Keep the entire `dist\Vega` folder together;
its `_internal` directory contains Qt, SDL, Python, and the application data.
No Python installation is needed to run that packaged folder. Build on
Windows using Python 3.13. Generated build outputs stay out of Git.

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
