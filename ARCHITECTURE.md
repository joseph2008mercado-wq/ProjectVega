# Project Vega architecture

## Product and current scope

Vega is a Windows 11 / Python 3.13 software-defined MIDI guitar controller.
It reads the Qanba Titan as an ordinary game controller; it does not replace,
suppress, or remap its Windows device. Concurrent access by a game remains a
hardware/driver test, not a guarantee. The eight faces establish harmonic state;
the lever performs a strum. Changing frets or Fret Sets alone never makes sound.

The implemented path is:

```text
Titan -> pygame/SDL raw events -> verified PC+DP profile -> symbolic physical state
                                                        |                 |
                                           active FretSet + faces     lever transitions
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
| OPTIONS | button 7 |

The two trigger-style axes start at 0, release near -1 and press near +1.
The profile ignores startup midpoint and uses release/press thresholds -0.5/+0.5.
DP is hat 0: x=-1/0/+1 means LEFT/neutral/RIGHT; y=-1/0/+1 means DOWN/center/UP.
Only `input/titan_profile.py` owns these IDs. The input profile, physical state,
and recognizer behavior are preserved. The recognizer merely exposes a read-only
`has_pending` property for safe bank switching.

Options is verified as ordinary pygame button 7 in PC+DP mode. The profile
translates it to `ButtonChange(ButtonControl.OPTIONS, pressed, timestamp)`.
Physical state tracks secondary buttons separately from fretting faces and
suppresses duplicate unchanged presses. The pipeline exposes its applied
symbolic edge as `last_change`; the runtime maps an OPTIONS press to
`BankAction.BANK_NEXT` (FRET_BANK_NEXT). Release performs no bank action.
Options never creates a stroke or schedules notes. A stroke already pending
from lever movement still finalizes normally with its captured bank/fingering.
GUI Previous/Next invoke the same bank behavior. Create/Share remains unmapped;
future secondary IDs belong only in the Titan profile. LS/RS remain unsupported.
Both raw and gesture inspectors remain independent of music/GUI/output code.

## Component responsibilities, structures and ownership

| Module | Responsibility / state owner |
| --- | --- |
| `input/events.py`, `pygame_titan.py`, `desktop_source.py` | Timestamped raw button/axis/hat events, selected controller handle, hotplug and SDL pumping. |
| `input/titan_profile.py`, `state.py`, `pipeline.py` | Raw-to-symbolic translation, held-face and secondary-button sets, lever x/y, applied symbolic edges, reset and recognizer invocation. |
| `music/strum.py` | Pending immutable `StrumGesture(direction, character, timestamp, fingering)` and horizontal rearm state. No music interpretation. |
| `music/fret_sets.py`, `harmony.py` | Authoritative immutable `FretSet(name, frets)` and three factory defaults; `FretSelection(bank, frets)` (bank is the internal set index), symbolic selection actions; immutable `Harmony(pitches, root, pitch_classes, intervals, identity)`. |
| `music/guitar.py` | Configurable `Fretboard(tuning)`, deterministic `voice`, `GuitarVoicing(strings)`, `VirtualString(string, note, fret)`; derived muted/open/fretted state. |
| `music/plan.py` | Coverage/velocity/duration profiles and pure `plan_strum`; immutable `StrumPlan(direction, character, notes)` with per-string note, velocity, offset and duration. |
| `midi/output.py` | Port lifecycle, deadline heap, active-note generation tokens, panic, Mido/RtMidi or PortMidi transport. |
| `audio/preview.py`, `pygame_backend.py` | Explicit playback permission, triangle PCM, bounded SDL voices, plan scheduling and failure containment. No chord decisions. |
| `runtime.py` | Owns input, active/queued bank, last gesture/selection/plan, both outputs and validated settings. Supplies immutable `ViewState`. |
| `app/` | Shows snapshots and forwards user actions. Qt layouts, dark Aero painting, native window identity. No raw IDs or note scheduling. |
| `settings.py` | Bounded timing/volume, Fret Sets/active set, MIDI port/channel and geometry; tolerant migration, retained unknown preferences and atomic save. |

Only the runtime loop mutates performance state. UI callbacks use runtime methods
or its MIDI service. Active set, selected port, channel and clamped geometry are
restored. Preview starts muted. Startup prefers exact “Vega Guitar” if present,
then the saved port; a missing port stays disconnected, never an arbitrary synth.
Settings writes are debounced; file failures are visible without stopping input.

## Fret Sets and harmony

`fret = active_set.frets[face.value - 1]` resolves each symbolic FACE control.
Exactly three immutable sets have eight integer slots in 1–24, with duplicate
values allowed. Factory definitions exist only in `music/fret_sets.py`:
Chromatic `(1,2,3,4,5,6,7,8)`, Major / Dominant `(2,4,5,7,9,10,11,12)`,
Minor / Blues `(2,3,5,6,7,8,10,12)`. Names never affect musical interpretation.
`FretSelection` sorts/deduplicates selected frets, while physical state retains
each held FACE independently. The existing internal `bank` index/action names
are retained to avoid unnecessary rewrites; the UI calls them Fret Sets.
Next/Previous wrap. Requests while any faces are held **or a stroke is pending**
are queued. Repeated requests advance the queued destination. Apply only after
both clear. Disconnect cancels a queued request. Runtime snapshots the immutable
mapping when a stroke starts settling, consumes it when that stroke finalizes,
and captures each immediate stroke separately. Queued switches and editor Save
cannot reinterpret a pending stroke, including multiple events in one batch.

The verified OPTIONS press uses this same safe queue: banks 1→2→3→1.
OPTIONS is outside the fingering set, so holding it cannot change harmony or
the captured FACE controls. Press/release alone produces no gesture, preview
audio or MIDI. Reset on disconnect rearms the secondary-button state.

Each selected fret gives pitch `40 + fret` (low E reference). Keep the exact
selected MIDI pitches; the lowest is the root anchor. Relative intervals are
deduplicated modulo 12. A small interval-name dictionary recognizes root/unison,
fifth, major, minor, dominant 7, major 7 and minor 7. Everything else is valid
`Custom`, not rejected or silent. No face combination table is necessary.

The Qt editor stages all three sets. Spin boxes constrain frets; names are trimmed,
limited to 40 characters and default to “Set N” when blank. Save validates and
atomically replaces the tuple, updates labels immediately and affects the next
new stroke. Cancel changes nothing. Resets copy factory definitions into staged
fields only. The dialog is window-modal but non-blocking; Qt timers keep running.
Settings deserialize the entire mapping configuration or use factory defaults;
other valid preferences survive. No cross-set held-note latching is introduced.

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

Startup prefers an exact “Vega Guitar” output, otherwise the saved selection.
Users may explicitly select/disconnect an existing output. Channel is 1–16 in the GUI,
converted to 0–15 on the wire. Note and velocity ranges are validated. A priority
queue sends note-on/off; active `(channel,note)` entries own generation tokens.
Retrigger sends off before on and invalidates the old release. Equal pitches on
two strings share a MIDI channel, so MIDI retriggers rather than providing
independent same-pitch string voices; per-string channels/MPE are deferred.

Both GUI Panic controls stop preview and cancel settling (without rearming a
held lever). MIDI Panic cancels all scheduled events, sends explicit offs, then sustain-off,
All Notes Off (CC123) and All Sound Off (CC120) on all channels of the selected
port. Use a dedicated Vega port. Channel/port changes, Titan disconnect, send
failure and shutdown clean up. Cleanup continues best-effort after individual
send failures. If the port/driver has vanished, delivery of panic cannot be
guaranteed; use the DAW panic command if necessary.

RtMidi can refresh connected-port enumeration; PortMidi caches its device list.
GUI **Refresh stops MIDI, closes the handle, reinitializes and reconnects the same
selection if available**. Queued notes are discarded, not replayed. The optional
read-only `windows_ports.output_signature()` uses WinMM's device names/IDs every
two seconds while connected; a changed inventory requests that same safe rescan.
Send failures also disconnect/clear scheduling. A missing chosen port is retained
as a preference, but only an explicit Refresh/selection retries it. There is no
fallback to an arbitrary output. Drivers that conceal inventory changes may
still require Refresh. MIDI problems do not stop input/preview.

Native Windows MIDI Services endpoint hosting is not implemented. Inspection on
Windows 11 25H2 build 26200.9457 found `midisrv` and the virtual transport, but no
installed App SDK runtime/tooling or verified Python integration. Microsoft's
virtual device API requires the new SDK and UMP-aware host/lifetime management;
the service alone is not evidence that Vega can publish a port. A tested native
bridge and DAW compatibility validation belong in a separate transport-only pass.
See the sourced investigation in `docs/RELEASE_INTEGRATION.md`.

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
Window geometry is saved through Qt, restored and clamped to the available screen.
The dedicated Fret Set dialog is compact and uses layouts/range-controlled widgets.

## Release / distribution layer

PyInstaller builds a console-free one-folder application with Python/Qt/SDL and
real Vega icon. The build collects installed and upstream version-matched license
notices, including the project's Unlicense. Inno Setup 6 then packages that folder
as `dist/installer/Vega-Setup.exe`: classic warm-gray/Tahoma wizard with per-window
unthemed controls and simple generated Vega bitmaps, per-user privileges,
stable `ProjectVega.Vega` AppId, `%LOCALAPPDATA%/Programs/Vega`, one Start Menu link
and an optional Desktop task. No runtime dependence on the installer or developer
tools. Version 0.2.0 is shared by project metadata, application and Setup.

Inno's install log manages upgrades/uninstall; user settings live outside the
installation and are never deleted. Legacy script-managed installations are
recognized by their ownership marker and upgraded in place: root payload and
matching shortcuts become current, old release folders/manifest remain as backups.
An existing legacy Desktop shortcut is retained even when the new task is unchecked.
Legacy helpers reject Setup-managed installs to avoid crossing ownership boundaries.
Setup rejects unrelated nonempty destinations and conflicting shortcuts. No EULA,
driver/service registration, auto-updater, admin hack or fabricated signature.
The test compiler variant changes only identity/destination/shortcut names for
safe disposable installation testing; production identity is unchanged.

## Repository structure

```text
src/vega/
  model.py, runtime.py, settings.py
  input/        events.py, titan_profile.py, state.py, pipeline.py,
                pygame_titan.py, desktop_source.py
  music/        strum.py, fret_sets.py, harmony.py, guitar.py, plan.py
  midi/         output.py, windows_ports.py
  audio/        preview.py, pygame_backend.py
  app/          __main__.py, window.py, widgets.py, style.py, geometry.py,
                identity.py, smoke.py, fret_set_editor.py, resources/
  diagnostics/  inspect_titan.py, inspect_gestures.py
tests/          input, music, preview, MIDI, runtime, settings, Qt and packaging checks
scripts/        build/install/uninstall/smoke Windows helpers
packaging/      Vega.spec, Vega.iss, windows-entry.py
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

Stable: Python 3.13; verified PC+DP mapping; symbolic-only musical input; three editable
Fret Sets; held-fret harmonic state; silent fret changes; open-state guitar; deterministic
voicing; shared plans; RIGHT low→high and LEFT high→low; FULL/NORMAL/STRICT coverage;
optional muted-start preview; existing-port MIDI; GUI-independent runtime.

Hardware/playing-dependent: Create/Share mapping, concurrent access, future
LS/RS profiles, latency and preferred spread/voicing feel. No driver, bends,
slides, capo, keyswitches, tuning UI or instrument-specific profiles in this stage.

1. **Done:** raw discovery, verified profile and deterministic gesture recognizer.
2. **Done:** desktop preview, identity, packaging and safe local shortcuts.
3. **Implemented:** harmony, fretboard/voicing, shared plans and MIDI routing.
4. **Release integration:** editable Fret Sets, robust existing-port MIDI and classic Setup.
5. **Next validation:** connect a real loopback port and FL Studio;
   play open/F-major strums, inspect spacing, retrigger notes and test panic/unplug.
6. **Later, measured improvements:** background/tray host, scheduling worker if
   justified, broader harmonic input policy, articulations and integrated endpoint.

## Beginner summary and next live check

The buttons choose musical notes; the voicer arranges them on six guitar strings.
The lever chooses how to sweep those strings. One plan goes to the small preview
synth and/or to a MIDI cable feeding a DAW. Input, music and transport remain separate.

Keep PC+DP and launch Vega:

```powershell
.\.venv\Scripts\python.exe -m vega.app
```

Press/release Options three times: the Fret Set display should cycle 1→2→3→1
without sound. Hold a FACE control and press Options: the current fret remains
unchanged until the faces and any pending stroke clear. Then connect the existing
MIDI cable to the DAW and verify open/F-major strokes, spacing and panic/unplug.
