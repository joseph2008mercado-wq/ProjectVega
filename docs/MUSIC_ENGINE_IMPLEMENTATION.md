# Musical-engine implementation report

## Delivered

Three arithmetic fret banks (1–8, 9–16, 17–24), queued bank switching, chromatic
harmonic input, common/custom interval recognition, configurable six-string
fretboard data, deterministic compact voicing, and one shared StrumPlan for
actual-pitch triangle preview and MIDI. Fret/bank changes never trigger notes.
The verified raw PC+DP profile and gesture behavior are unchanged.

Options is **unverified**. Previous/Next GUI actions work now; no secondary raw
button ID was guessed. A bank request waits for released faces and any pending
stroke. Every launch starts on bank 1 with preview muted and MIDI disconnected.

Bank 1 frets 1/5/8 select F major. Generated strings 6→1:
F2, C3, F3, A3, C4, F4; frets 1,3,3,2,1,1. Empty selection is exactly the open
guitar E2,A2,D3,G3,B3,E4. Unknown selections remain Custom pitch/interval sets.
The bounded eight-candidate search favors chord-tone coverage, root bass, fewer
mutes and compact fret spans; it is not a physical-playability solver.

FULL covers six available strings, NORMAL the highest four, STRICT the highest
three. RIGHT sweeps low→high; LEFT reverses. Velocities are 110/90/72. Default
inter-string spread is 10 ms, separate from 8 ms gesture settling. Preview and
MIDI consume identical pitches, velocities, offsets, durations and start epoch.

MIDI uses Mido encoding, with optional RtMidi or pygame's bundled PortMidi.
The default Windows/Python 3.13 install uses PortMidi because published RtMidi
wheels stop at Python 3.12. No compiler or new driver is required by the desktop
extra. No native virtual endpoint is created. The scheduler handles on/off,
active notes, generation-safe retriggers, channel selection, panic and shutdown.
Refresh stops/disconnects MIDI before rescanning; reselect a port afterward.

## Verification

- Full Python 3.13.14 suite: **78 passed**, no failures or skips.
- Separate Qt window test processes at 125% and 150%: **3 passed each**.
- Windows install-helper path/ownership checks: passed.
- Windows executable build and native smoke check: passed; real Titan detected,
  GUI/icon loaded, no console, preview muted, bank 1 and correct open tuning.
- Native smoke check reported **150% device pixel ratio**, 900×940 logical window.
- Qt layouts tested at 900×940, 860×600, 780×580, 640×440, 480×350 and the
  400×300 minimum. Narrow layouts stack and all tested controls can be scrolled
  fully into view without horizontal scrolling.
- Sizing policy tested against 1280×720, 1366×768 and 1920×1080 at 100/125/150%,
  accounting for available desktop space. These modeled resolutions are not
  claims of nine physical-monitor tests. No stale geometry is restored.
- Normal and narrow panel renders inspected with Segoe UI; existing plum
  Vista/Aero identity retained.
- Actual Windows MIDI enumeration succeeded through PortMidi. Only Microsoft
  MIDI Mapper and Microsoft GS Wavetable Synth were present, not Vega Guitar.

Not yet verified: an audible FL Studio/VST loopback session, live MIDI timing
under load, port-loss recovery with a real cable, or Options' raw mapping.
Digital lever velocity remains profile-based. Seventh-chord interval structures
are supported in musical data, but most cannot be held in one eight-fret bank.

## Install and DAW check

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[desktop]"
.\.venv\Scripts\python.exe -m vega.app
```

Create/enable an existing loopback cable named Vega Guitar. In Vega select
Refresh → Vega Guitar, keep channel 1, confirm Connected. In FL Studio:
Options → MIDI settings → Input → Vega Guitar → Enable → (generic controller).
Select a loaded instrument channel, keep preview muted and try an open FULL
stroke, then frets 1/5/8. Record notes to inspect onset spacing; test Panic and
Titan unplug. Do not feed the DAW output back into the same cable. The full
setup, troubleshooting and exact Options-discovery command are in README and
ARCHITECTURE. System synth outputs alone do not feed FL Studio.

## Every changed or added source file

| File | Change |
| --- | --- |
| `ARCHITECTURE.md` | Current implemented pipeline, ownership, algorithms, timing, hardware boundary, MIDI constraints and future work. |
| `README.md` | Playing instructions, banks, actual preview, existing-port MIDI/FL workflow and dependency caveat. |
| `docs/MUSIC_ENGINE_IMPLEMENTATION.md` | This delivery and verification report. |
| `pyproject.toml` | Compiler-free desktop/MIDI extras and optional RtMidi extra. |
| `packaging/Vega.spec` | Include dynamically loaded MIDI backends in the Windows executable. |
| `src/vega/app/__main__.py` | Refresh MIDI at startup and inject the production clock. |
| `src/vega/app/geometry.py` | New screen-clamped logical-pixel sizing policy. |
| `src/vega/app/smoke.py` | Report bank, strings, ports, size and DPI in packaged smoke mode. |
| `src/vega/app/style.py` | Match new MIDI/spin controls to the existing theme. |
| `src/vega/app/widgets.py` | Actual fret labels/accessibility; practical instrument minimum sizes. |
| `src/vega/app/window.py` | Bank, harmony, strings, spread, MIDI and responsive scrolling controls. |
| `src/vega/audio/__init__.py` | Update package description for shared plans. |
| `src/vega/audio/preview.py` | Actual-plan synthesis, note PCM, headroom and output scheduling interface. |
| `src/vega/audio/pygame_backend.py` | Cached notes and bounded timed string-channel groups. |
| `src/vega/midi/__init__.py` | New MIDI package boundary. |
| `src/vega/midi/output.py` | Transport adapters, deadline scheduler, cleanup, failures and panic. |
| `src/vega/music/guitar.py` | New fretboard, virtual strings and deterministic bounded voicer. |
| `src/vega/music/harmony.py` | New arithmetic banks, selection and harmony interpretation. |
| `src/vega/music/plan.py` | New shared coverage profiles and scheduled strum representation. |
| `src/vega/music/strum.py` | Read-only pending-stroke property; recognizer behavior unchanged. |
| `src/vega/runtime.py` | Musical state/bank ownership, shared-plan delivery and MIDI lifecycle. |
| `src/vega/settings.py` | Validated/persisted string spread, backward-compatible load. |
| `tests/test_midi.py` | New deterministic transport, timing, note lifecycle and failure tests. |
| `tests/test_music.py` | New bank/fretboard/harmony/voicing/coverage and validation tests. |
| `tests/test_preview.py` | Replace obsolete fixed-chord assertions with shared-plan/PCM/cache tests. |
| `tests/test_runtime.py` | Silent changes, safe queued banks, batching, shared plans and epoch tests. |
| `tests/test_settings.py` | Spread validation and persistence coverage. |
| `tests/test_window.py` | Musical/MIDI GUI state, sizing policy and scroll reachability tests. |

Build artifacts and temporary smoke reports remain ignored. No Titan input
profile, raw inspector, gesture inspector, icon art or unrelated code was changed.
