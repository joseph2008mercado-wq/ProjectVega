# Project Vega

The standalone Qanba Titan input inspector records what pygame/SDL exposes on
Windows. A separate, unit-tested PC+DP input layer now translates the verified
main controls and recognizes symbolic strum gestures. It does not interpret
chords or send MIDI. See [ARCHITECTURE.md](ARCHITECTURE.md) for the mapping and
planned instrument.

In PC+DP mode, horizontal lever movement starts LEFT or RIGHT strums; the
vertical position marks them FULL (down), NORMAL (center), or STRICT (up).
Returning horizontally to x=0 rearms the next stroke even if up/down remains
held. The eight main face controls include two trigger-style axes, normalized
to ordinary symbolic presses and releases in the Titan profile.

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
