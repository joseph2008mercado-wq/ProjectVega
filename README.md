# Project Vega

The first stage is a standalone Qanba Titan input inspector. It records what
pygame/SDL exposes on Windows; it does not map controls to chords or send MIDI.
See [ARCHITECTURE.md](ARCHITECTURE.md) for the planned instrument.

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

Send back the three session logs plus the physical order in which you tested
the eight main buttons and any controls that produced no events. The useful
parts are the `SESSION` and `INITIAL` lines (device identity/counts),
`BASELINE`, all `BUTTON`/`HAT`/`AXIS` lines during the checklist, and any
`CONNECTED`/`DISCONNECTED` lines after unplugging or changing mode. Also say
whether events continued while another app had focus and whether a gamepad
tester still saw ordinary Titan input at the same time. These observations
will determine the first reviewed Titan profile.
