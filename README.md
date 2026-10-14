# Project Vega

A Windows 11 / Python 3.13 desktop control panel for Qanba Titan gestures,
with optional triangle-based preview audio. The PC+DP input profile and 8 ms
gesture behavior have been validated on real hardware. MIDI, FL Studio/VST
output, and final chord/voicing interpretation are not implemented yet.
See [ARCHITECTURE.md](ARCHITECTURE.md) for the mapping and planned instrument.

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

The plum-glass panel shows held FACE controls, the eight-way lever, and the
last strum's immutable fingering snapshot. Adjust the production settle window
live from 0–20 ms, with shortcuts for 4/6/8/10/12 ms. **8 ms is the current
verified default, still adjustable and experimental.** A change also updates
the deadline of an already pending gesture at the next input tick.

Preview audio **starts muted on every launch**. Unmute for triangle-based
multi-note strums: FULL uses six notes with 12 ms spacing and longer decay;
NORMAL uses four with 9 ms spacing; STRICT uses three higher notes with 6 ms
spacing and shorter decay. RIGHT sweeps low to high; LEFT reverses the order.
The fixed preview-only E-major pitches ignore fingering. Gain is stronger,
with headroom for three overlapping strums; the oldest is replaced when full.
New settings default to 65% volume; your saved volume is preserved.
Mute stops active audio;
Panic stops current voices while allowing later gestures if still unmuted.
Audio failure leaves input visualization running; restart Vega to retry audio.

Settle time and volume save to `%LOCALAPPDATA%\ProjectVega\settings.json`.
Mute permission is never saved. The future primary output remains MIDI to a
DAW/VST, independently of this optional preview.

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
