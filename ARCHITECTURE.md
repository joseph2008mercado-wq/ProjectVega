# Project Vega architecture

## Product and current scope

Vega is a Windows 11 / Python 3.13 software-defined MIDI guitar controller.
It reads the Qanba Titan as an ordinary game controller; it does not replace,
suppress, or remap its Windows device. Concurrent access by a game remains a
hardware/driver test, not a guarantee. The eight faces establish harmonic state;
the lever performs a strum. Changing frets or banks alone never makes sound.

The implemented path is:

```text
Titan -> pygame/SDL raw events -> verified PC+DP profile -> symbolic physical state
                                                        |                 |
                                              bank + held faces       lever transitions
                                                        |                 |
                                                  FretSelection      StrumRecognizer
                                                        |                 |
                                                     Harmony              |
                                                        |                 |
                                                   GuitarVoicing          |
                                                  six VirtualStrings      |
                                                        +----- StrumGesture
                                                                  |
                                                               StrumPlan
                                                             /          \
                                                   Preview synth      MIDI scheduler
                                                                          |
                                                                  existing output port
                                                                          |
                                                                  DAW input -> instrument
```

These are responsibilities, not separate processes or a class for every arrow.
The music code is pure Python. One runtime, two optional outputs, and a small
Qt panel are sufficient for this stage. There is no service, database, plugin
framework, driver or DAW-specific behavior.

## End-user DAW workflow

1. Enable an existing Windows MIDI loopback cable, optionally named **Vega Guitar**.
2. Start Vega with the Titan switches at **PC + DP**, buttons released, lever centered.
3. Select that exact output in Vega; select its matching input in the DAW.
4. Enable the DAW input and select/arm a software instrument. Hold frets, then strum.
5. Preview can remain muted: MIDI and preview are independent.

Vega does **not** create the Windows endpoint. The cable supplies a DAW input
and Vega output. Mido/RtMidi cannot create virtual ports on Windows through its
usual virtual-port API ([Mido documentation](https://mido.readthedocs.io/en/stable/backends/rtmidi.html)).
Windows MIDI Services endpoint publication is deferred behind the transport boundary.

## Verified hardware boundary

The real Titan was tested on Windows 11, Python 3.13.14, pygame 2.6.1 and SDL
2.28.4 in **PC system / DP lever** mode: 11 buttons, 6 axes, 1 hat.

| Symbol | Raw pygame control |
| --- | --- |
| FACE_1 | button 2 |
| FACE_2 | button 3 |
| FACE_3 | button 5 |
| FACE_4 | button 4 |
| FACE_5 | button 0 |
| FACE_6 | button 1 |
| FACE_7 | axis 5 |
| FACE_8 | axis 4 |

The two trigger-style axes start at 0, release near -1 and press near +1.
The profile ignores startup midpoint and uses release/press thresholds -0.5/+0.5.
DP is hat 0: x=-1/0/+1 means LEFT/neutral/RIGHT; y=-1/0/+1 means DOWN/center/UP.
Only `input/titan_profile.py` owns these IDs. The input profile, physical state,
and recognizer behavior are preserved. The recognizer merely exposes a read-only
`has_pending` property for safe bank switching.

Options and Create/Share do **not** have authoritative mappings in this repository.
GUI buttons invoke symbolic `BankAction.BANK_NEXT` and `BANK_PREVIOUS`; neither
has a guessed raw binding. Future verified secondary IDs belong only in the
Titan profile. LS/RS remain unsupported. Both raw and gesture inspectors remain
independent of the music/GUI/output code.

## Component responsibilities, structures and ownership

| Module | Responsibility / state owner |
| --- | --- |
| `input/events.py`, `pygame_titan.py`, `desktop_source.py` | Timestamped raw button/axis/hat events, selected controller handle, hotplug and SDL pumping. |
| `input/titan_profile.py`, `state.py`, `pipeline.py` | Raw-to-symbolic translation, held-face set, lever x/y, reset and recognizer invocation. |
| `music/strum.py` | Pending immutable `StrumGesture(direction, character, timestamp, fingering)` and horizontal rearm state. No music interpretation. |
| `music/harmony.py` | `FretSelection(bank, frets)`, symbolic bank actions, immutable `Harmony(pitches, root, pitch_classes, intervals, identity)`. |
| `music/guitar.py` | Configurable `Fretboard(tuning)`, deterministic `voice`, `GuitarVoicing(strings)`, `VirtualString(string, note, fret)`; derived muted/open/fretted state. |
| `music/plan.py` | Coverage/velocity/duration profiles and pure `plan_strum`; immutable `StrumPlan(direction, character, notes)` with per-string note, velocity, offset and duration. |
| `midi/output.py` | Port lifecycle, deadline heap, active-note generation tokens, panic, Mido/RtMidi or PortMidi transport. |
| `audio/preview.py`, `pygame_backend.py` | Explicit playback permission, triangle PCM, bounded SDL voices, plan scheduling and failure containment. No chord decisions. |
| `runtime.py` | Owns input, active/queued bank, last gesture/selection/plan, both outputs and validated settings. Supplies immutable `ViewState`. |
| `app/` | Shows snapshots and forwards user actions. Qt layouts, dark Aero painting, native window identity. No raw IDs or note scheduling. |
| `settings.py` | Bounded settle, string spread and preview volume; tolerant load and atomic save. |

Only the runtime loop mutates performance state. UI callbacks use runtime methods
or its MIDI service. Bank, port, channel and preview permission start fresh;
bank 1, no connected MIDI output, channel 1, preview muted. No geometry is persisted.
Settings writes are debounced; file failures are visible without stopping input.

## Fret banking and harmony

`fret = (bank - 1) * 8 + face.value` maps banks 1/2/3 to 1–8/9–16/17–24.
Next/Previous wrap. Requests while any faces are held **or a stroke is pending**
are queued. Repeated requests advance the queued destination. Apply only after
both clear. Disconnect cancels a queued request. At each finalized gesture the
runtime captures its active bank before applying a waiting change, including
when multiple events arrive in one batch. A captured fingering is never
reinterpreted under the next bank.

Each selected fret gives pitch `40 + fret` (low E reference). Keep the exact
selected MIDI pitches; the lowest is the root anchor. Relative intervals are
deduplicated modulo 12. A small interval-name dictionary recognizes root/unison,
fifth, major, minor, dominant 7, major 7 and minor 7. Everything else is valid
`Custom`, not rejected or silent. No face combination table is necessary.

**Bank limitation:** all simultaneously held frets must come from the same
eight-fret bank. Some recognized chord structures, notably sevenths, require
wider chromatic spans and are not directly playable with this bank policy yet.
The interpreter supports them as musical data; this stage does not add latching
or cross-bank held notes. This is an intentional consequence of the requested
input scheme, not an extra hidden chord-expansion rule.

An empty selection bypasses harmony search and returns exactly E2 A2 D3 G3 B3 E4.
The system is a harmonic controller, not a literal six-string fingering input:
the selected pitches determine pitch classes; the voicer chooses guitar registers.

## Fretboard and voicing algorithm

Tuning is a six-element MIDI tuple `(40,45,50,55,59,64)`, low to high, strings
6 through 1. `note = tuning[6 - string] + fret`, with frets 0–24. Tuning is
injectable data; there is no alternate-tuning UI or 150-note lookup table.

For non-open harmony:

1. Search five-fret windows starting at frets 1 through 20. Each string can use
   a matching chord tone in that window, a matching open string, or mute.
2. Extend from string 6 to string 1. Keep the best eight partial candidates at
   each string (bounded beam search). Reject descending sounding pitch order.
3. Score missing pitch classes at 1000 each, non-root bass at 120, muted strings
   at 12, fretted span at 2 per fret, total stopped frets at 0.1 each and bass
   pitch at 0.02. Equal scores break by the fret tuple, with mute after fret 24.
4. Choose the best complete candidate across windows; cache up to 256 harmonies.

Thus chord-tone coverage dominates, then root bass, full coverage and compactness.
Duplicated chord tones are allowed, all notes belong to the harmony, stopped
frets span at most four semitones, and notes rise with string order. This is a
deterministic playable-looking heuristic, **not** proof of human fingering
playability or a global optimum. Dense custom sets can contain more pitch classes
than six strings can voice; the complete original harmony is still retained.

Example: bank 1 frets **1, 5, 8** select F2 A2 C3, recognized as F major.
One generated six-string result is **F2 C3 F3 A3 C4 F4**, with frets
**1, 3, 3, 2, 1, 1** on strings 6→1.

## Gesture, strumming and timing

The verified recognizer produces one stroke on x=0→±1. Only returning x to 0
rearms; vertical-only movement never sounds. A default 8 ms settle window
absorbs intermediate diagonal events, preserving the first timestamp/faces.
Nonzero y during settling refines character. Changing the live 0–20 ms settle
setting changes the pending deadline without duplicating a stroke.

| Character | Coverage of available strings | Velocity | Duration per note |
| --- | --- | --- | --- |
| FULL (down) | All, normally 6 including bass | 110 | 800 ms |
| NORMAL (vertical center) | Highest 4 | 90 | 600 ms |
| STRICT (up) | Highest 3 | 72 | 350 ms |

Muted strings are skipped. RIGHT orders low string→high; LEFT reverses. The
same shared profiles determine MIDI and preview. Velocity is a fixed character
value, not measured lever force. String spread defaults to **10 ms**, adjustable
1–30 ms, independent of gesture settle. Plan offsets are 0, spread, 2×spread, …;
note-off is offset+duration. No fret/bank/harmony update schedules anything.

Production uses `perf_counter()` and a 2 ms precise Qt timer. After finalizing
and planning, the runtime samples a fresh start time and passes that **same epoch
and plan** to both outputs. Tests inject times (and optionally a clock) without
sleep. Pending output events use absolute deadlines and stable tie ordering.
Late ticks drain due events; they do not add cumulative relative sleeps.

This remains best-effort desktop timing, not hard realtime. UI repaint, voicing
search, port enumeration and Windows scheduling can delay a tick. PCM generation
is moved to startup; voicing search is bounded/cached. Measure real strum spacing
under load before considering a scheduling worker. Output-device and DAW audio
buffers add latency even when MIDI and preview share a plan.

## Preview output

Preview starts muted on every launch and consumes actual plan pitches, velocities,
offsets and durations. No fixed E-major audition chord remains. Triangle PCM is
prebuilt at startup for 128 MIDI notes × three profile durations, avoiding live
wave synthesis. Six SDL channels form a strum group; three groups can overlap.
A fourth replaces the oldest group, cancelling its future onsets too. Per-string
gain is bounded to 0.30/6, so 18 aligned voices remain below 0.90 full scale.
Mute/panic stops both queued and sounding preview notes. Errors disable preview
without disabling visualization or MIDI. Startup synthesis adds a few seconds;
it is not a sampled guitar and high MIDI pitches are only a simple audition.

## MIDI output architecture and cleanup

`MidiOutput` takes an injected `MidiBackend` with ports/open/send/close methods.
The default adapter validates/encodes messages with **Mido 1.3.3** and prefers
RtMidi if installed. The published `python-rtmidi 1.5.8` lacks a Python 3.13
Windows wheel; installing it here requires a C++ compiler. The default desktop
extra therefore uses pygame's bundled **PortMidi** transport, with optional
`.[rtmidi]` for environments that can build RtMidi. This keeps Python 3.13 and
does not require an untrusted third-party binary ([RtMidi releases](https://pypi.org/project/python-rtmidi/),
[pygame MIDI](https://www.pygame.org/docs/ref/midi.html)).

The user explicitly selects an existing output. Channel is 1–16 in the GUI,
converted to 0–15 on the wire. Note and velocity ranges are validated. A priority
queue sends note-on/off; active `(channel,note)` entries own generation tokens.
Retrigger sends off before on and invalidates the old release. Equal pitches on
two strings share a MIDI channel, so MIDI retriggers rather than providing
independent same-pitch string voices; per-string channels/MPE are deferred.

Panic cancels all scheduled events, sends explicit offs, then sustain-off,
All Notes Off (CC123) and All Sound Off (CC120) on all channels of the selected
port. Use a dedicated Vega port. Channel/port changes, Titan disconnect, send
failure and shutdown clean up. Cleanup continues best-effort after individual
send failures. If the port/driver has vanished, delivery of panic cannot be
guaranteed; use the DAW panic command if necessary.

RtMidi can refresh connected-port enumeration; PortMidi caches its device list
while initialized. GUI **Refresh disconnects/stops MIDI**, reinitializes the
disconnected backend and rescans. Select the output again afterward. With
PortMidi, disappearance detection while connected relies primarily on send
errors; silent driver loss may require Refresh/restart. No automatic fallback to
another port and no automatic reconnect that unexpectedly resumes sound.

## Runtime, desktop and future background host

`VegaRuntime.tick(now)` polls input, applies connection resets, finalizes gestures,
captures bank+fingering, creates plans and services outputs even on idle ticks.
A disconnect later in an input batch discards earlier ready strokes in that
batch. The runtime has no Qt import and can be hosted independently later.
SDL must be pumped by its owning thread. Today closing the panel closes the
runtime; a tray/service host and single-instance enforcement remain future work.
Run only one Vega app/diagnostic at a time.

The panel retains the plum Vista/Aero identity, Segoe UI, champagne accents and
claw/six-string mark. Frets, harmonic state and six strings are read-only displays.
Responsive box/grid layouts stack below 780 logical pixels. A resizable
`QScrollArea` makes short windows scroll; the 400×300 logical minimum is modest.
Default size is at most 900×940, clamped inside current available screen bounds
with titlebar/taskbar space. Qt logical pixels account for display scaling.
No window geometry is persisted, so stale off-screen restoration cannot occur.

## Repository structure

```text
src/vega/
  model.py, runtime.py, settings.py
  input/        events.py, titan_profile.py, state.py, pipeline.py,
                pygame_titan.py, desktop_source.py
  music/        strum.py, harmony.py, guitar.py, plan.py
  midi/         output.py
  audio/        preview.py, pygame_backend.py
  app/          __main__.py, window.py, widgets.py, style.py, geometry.py,
                identity.py, smoke.py, resources/
  diagnostics/  inspect_titan.py, inspect_gestures.py
tests/          input, music, preview, MIDI, runtime, settings, Qt and packaging checks
scripts/        build/install/uninstall/smoke Windows helpers
packaging/      Vega.spec, windows-entry.py
```

## Testing and technical risks

Automated tests use fake input/audio/MIDI and injected timestamps, never Titan,
FL Studio, speakers or arbitrary sleeps. They cover unchanged input behavior;
bank mapping/wrap/queue and silent changes; fretboard landmarks; common/custom
harmony; root bass, compactness and deterministic voicing; coverage/order/timing;
actual preview pitches; MIDI message encoding, deadlines, retrigger, panic,
port errors and fallback; GUI snapshots, port controls and scroll reachability.
Qt tests exercise 900×940, 860×600, 780×580, 640×440, 480×350 and minimum-window
layouts. Geometry tests model 1280×720, 1366×768 and 1920×1080 at 100/125/150%.
These are layout/DPI assumptions, not certification on nine physical monitors.

Real playing tests still need to establish end-to-end latency, Windows focus and
concurrent controller access, port hotplug reliability, DAW/VST note release,
and whether compact heuristic voicings feel good. The runtime must not claim
hardware-derived force or hard realtime timing. High-DPI/native rendering and
the frozen executable receive separate smoke checks.

## Stable decisions and next stages

Stable: Python 3.13; verified PC+DP mapping; symbolic-only musical input; arithmetic
banks; held-fret harmonic state; silent fret changes; open-state guitar; deterministic
voicing; shared plans; RIGHT low→high and LEFT high→low; FULL/NORMAL/STRICT coverage;
optional muted-start preview; existing-port MIDI; GUI-independent runtime.

Hardware/playing-dependent: Options/Create mapping, concurrent access, future
LS/RS profiles, latency and preferred spread/voicing feel. No driver, bends,
slides, capo, keyswitches, tuning UI or instrument-specific profiles in this stage.

1. **Done:** raw discovery, verified profile and deterministic gesture recognizer.
2. **Done:** desktop preview, identity, packaging and safe local shortcuts.
3. **Implemented now:** banks, harmony, fretboard/voicing, shared plans and MIDI routing.
4. **Next validation:** identify Options; connect a real loopback port and FL Studio;
   play open/F-major strums, inspect spacing, retrigger notes and test panic/unplug.
5. **Later, measured improvements:** background/tray host, scheduling worker if
   justified, broader harmonic input policy, articulations and integrated endpoint.

## Beginner summary and exact next hardware task

The buttons choose musical notes; the voicer arranges them on six guitar strings.
The lever chooses how to sweep those strings. One plan goes to the small preview
synth and/or to a MIDI cable feeding a DAW. Input, music and transport remain separate.

Next, close Vega, keep PC+DP, run:

```powershell
.\.venv\Scripts\python.exe -m vega.diagnostics.inspect_titan --mode DP --log titan-options.txt
```

Leave other controls untouched; press/release Options three times, then optionally
Create/Share three times, noting that order. Send the SESSION/INITIAL/BASELINE
lines and changed BUTTON/AXIS/HAT lines (or report no events). Only that evidence
should establish the remaining physical bank-action mapping.
