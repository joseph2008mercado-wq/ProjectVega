# Project Vega architecture

## Product definition

Project Vega is a Windows-first, Python 3.13 application that reads a Qanba Titan arcade fight stick and turns performance gestures into MIDI for a DAW. The Titan remains usable as a normal game controller: Vega reads its controller events and does not remap, suppress, or replace them. Whether simultaneous access works with the actual Titan mode, driver, and games must be verified on hardware.

The first instrument is **Vega Guitar**. Eight face buttons represent a held fingering. The joystick represents the picking hand: its horizontal component starts a LEFT or RIGHT stroke, while its vertical component selects FULL, NORMAL, or STRICT strum character. A recognized stroke captures the current fingering, resolves its harmony, chooses a six-string guitar voicing, and schedules ordered MIDI notes. The DAW receives MIDI; a VST or other software instrument produces sound. Vega itself is not an audio engine or a guitar sample library.

The first release should make a small, playable set of fingerings reliable. It should not attempt to infer arbitrary chords from all 256 button combinations or simulate every physical guitar technique.

## End-user DAW workflow

1. Connect the Titan and launch the Vega background runtime.
2. In the initial Windows setup, create or enable an external virtual MIDI loopback port named **Vega Guitar**. Select that port as Vega's MIDI output.
3. In Ableton, FL Studio, REAPER, or another DAW, enable **Vega Guitar** as a MIDI input and route it to an armed instrument track.
4. Hold a supported button combination and move the joystick to strum. The DAW receives MIDI note-on and note-off messages; its instrument supplies the sound.

The port is the DAW's **input** and Vega's **output**. The friendly name comes from the loopback endpoint in the first implementation, not from `mido.open_output()` creating a device. Mido/RtMidi's own virtual-port creation is unavailable on Windows [Mido virtual ports](https://mido.readthedocs.io/en/stable/intro.html#virtual-ports), [python-rtmidi virtual ports](https://spotlightkid.github.io/python-rtmidi/rtmidi.html#rtmidi.MidiOut.open_virtual_port). A later Windows MIDI Services adapter may publish the endpoint directly, subject to deployment and DAW compatibility testing [Windows MIDI Services virtual devices](https://microsoft.github.io/MIDI/sdk-reference/Transports/Virtual/).

## Architectural overview

There are three practical parts:

| Part | Responsibility | Knows about |
| --- | --- | --- |
| Input adapter/profile | Read SDL/pygame events for one selected Titan; translate verified PC+DP raw controls | pygame at the adapter edge, device IDs, raw axes/hats/buttons |
| Symbolic state/gesture layer | Maintain held faces and lever x/y; recognize horizontal strokes and capture immutable fingerings | symbolic controls and monotonic time; no pygame or MIDI library |
| Musical engine | Interpret fingerings; resolve harmony and voicing; plan timed notes | symbolic gestures, pitch, time; no pygame or MIDI library |
| Output/runtime | Deliver scheduled MIDI events, manage port and lifecycle, report errors | Mido/RtMidi, monotonic clock, configuration |

The logical flow is:

```text
Titan -> pygame/SDL -> raw events -> PC+DP profile -> symbolic faces + lever x/y
                                                        |
                                                        v
                                                physical input state
                                                  /            \
                                      held faces snapshot    lever x/y
                                                  \            /
                                               stroke recognizer
                                          (LEFT/RIGHT + character)
                                                        |
                                               fingering/chord model
                                                        |
                                                 guitar voicing
                                                        |
                                                  strum planner
                                                        |
                                          MIDI scheduler/output -> DAW
```

This is a dependency diagram, not a mandate for one Python class per box. The fingering and gesture branches meet when a stroke is recognized. At that instant, the runtime takes a snapshot of the held fingering; subsequent button changes affect the next stroke, not already scheduled notes.

## Components and responsibilities

| Component | Input | Output / owned responsibility |
| --- | --- | --- |
| `PygameTitanInput` | pygame joystick queue | Raw button, hat, and axis events with device instance ID and receive time; connect/disconnect signals. Pump the SDL queue regularly. |
| `TitanPcDpProfile` | Raw button, axis, and hat events | Symbolic `FACE_1` through `FACE_8` changes and lever `(x, y)` changes. It owns all verified PC+DP pygame IDs and trigger-axis thresholds. |
| `PhysicalState` | Symbolic face and lever changes | Currently held face controls and lever x/y. It exposes immutable fingering snapshots. |
| `Fingering` | Snapshot of held face controls | Immutable set or 8-bit mask of controls; does not claim a specific chord until interpreted. |
| `FingeringInterpreter` | Fingering and active mapping | A harmonic choice such as root E and major triad intervals; unsupported fingerings return `None` with no new notes. |
| `Chord` / `Intervals` | Root pitch class and interval tuple | Pitch-independent harmonic meaning, e.g. major `(0, 4, 7)`; optional bass/inversion hint. |
| `GuitarVoicer` | Chord and voicing preset | Ordered six-string snapshot: one MIDI pitch or mute per virtual string. The initial voicer uses explicit, reviewed templates for supported chords rather than a complex fingering solver. |
| `VirtualString` | String ID, pitch, mute flag | A musical lane for ordering and coverage. It does not read hardware or send MIDI. |
| `StrumRecognizer` | Symbolic lever transitions, timestamps, and fingering snapshots | One `StrumGesture` on horizontal acquisition after x=0; direction LEFT/RIGHT, character from y, original timestamp and fingering. A short deterministic settle window handles intermediate diagonal events. |
| `StrumPlanner` | Gesture, voicing snapshot, strum preset | Ordered, absolute-deadline note-on and note-off intentions with chosen velocity and coverage. Pure logic. |
| `MidiScheduler` | Planned events and monotonic time | Due events in a small priority queue; handles cancellation and active-note bookkeeping without blocking input polling. |
| `MidiOutput` | Semantic note-on, note-off, panic | Opens an existing named MIDI output port and sends messages. A fake implementation supports tests. |
| `VegaRuntime` | Adapters, config, clock | Starts and stops components, connects the selected device/port, owns the loop, and coordinates recovery. |

The future settings interface edits validated configuration and displays status. It is a separate process or thin client of the background runtime, never the owner of the input loop or active notes. Start without a GUI; a configuration file and readable logs are enough for the prototype.

## Data flow and important data structures

Use small frozen dataclasses and enums in the engine. For example:

```text
RawButtonEvent / RawAxisEvent / RawHatEvent(..., timestamp, instance_id)
FaceChange(face, pressed, timestamp) | LeverChange(x, y, timestamp)
PhysicalState(held_faces, lever_x, lever_y)
Fingering(faces: frozenset[FaceControl])
Chord(root_pitch_class, intervals, bass_hint=None)
VirtualString(id, open_pitch, sounding_pitch: int | None)
Voicing(strings: tuple[VirtualString, ...])  # low string to high string
StrumGesture(direction, character, timestamp, fingering)
PlannedMidiEvent(due_at_ns, order, kind, channel, pitch, velocity, string_id)
```

The current `TitanPcDpProfile` holds the verified mapping in one small module. It normalizes the two trigger-style axes with tolerant press/release thresholds and ignores their startup 0.0. Future mode profiles or editable data can use the same symbolic interface. A future input adapter must select the intended device and pass its events to this profile; runtime instance IDs identify a connection and are never persisted as control mappings. Pygame documents event pumping, device-added/removed events, and instance IDs [pygame joystick documentation](https://www.pygame.org/docs/ref/joystick.html).

### Verified Qanba Titan PC + DP profile

The real controller was tested on Windows 11 with Python 3.13.14, pygame 2.6.1, and SDL 2.28.4 in physical **PC system / DP lever** mode. SDL reported 11 buttons, 6 axes, and 1 hat. The eight main controls, in physical test order, are:

| Symbolic control | Pygame control |
| --- | --- |
| `FACE_1` | button 2 |
| `FACE_2` | button 3 |
| `FACE_3` | button 5 |
| `FACE_4` | button 4 |
| `FACE_5` | button 0 |
| `FACE_6` | button 1 |
| `FACE_7` | axis 5 |
| `FACE_8` | axis 4 |

Axes 4 and 5 are digital trigger-style controls: startup can report 0.0, release settles near -1, and press near +1. The profile treats the startup midpoint as no change and uses thresholds rather than exact float equality. DP lever movement is pygame hat 0: x=-1/0/+1 means LEFT/horizontal neutral/RIGHT; y=-1/0/+1 means DOWN/vertical center/UP. Its nine tuples cover center, four cardinal directions, and four diagonals. These raw IDs remain inside the profile; all higher layers see symbolic controls only. LS and RS mappings are not established.

The initial fingering map is explicit: a defined face-control set maps to a `Chord` (and optionally a voicing preset). An empty or unrecognized set has a documented behavior: no new strum; already sounding notes continue until their scheduled release. This is predictable and easy to test. Add richer interval rules only after actual playing reveals a need.

For the E-major example, one voicing snapshot is `(E2, B2, E3, G#3, B3, E4)` from lowest to highest virtual string. In MIDI note numbers (C4 = 60), that is `(40, 47, 52, 56, 59, 64)`. These are sounding pitches; the physical Titan buttons are not literal guitar frets or strings.

## Module boundaries and state ownership

Proposed interfaces are intentionally narrow:

```text
InputSource.poll() -> list[RawEvent]                  # future pygame adapter
TitanPcDpProfile.translate(raw_event) -> ControlChange | None
VegaInputPipeline.on_raw(raw_event) -> list[StrumGesture]
VegaInputPipeline.flush(now) -> list[StrumGesture]
MusicalEngine.on_gesture(gesture) -> list[PlannedMidiEvent]  # later stage
Scheduler.add(events); Scheduler.pop_due(now_ns) -> list[PlannedMidiEvent]
MidiOutput.send(event); MidiOutput.all_notes_off(); MidiOutput.close()
Clock.now_ns() -> int
```

The future runtime loop owns the input pipeline (`TitanPcDpProfile`, `PhysicalState`, and `StrumRecognizer`), event scheduler, and selected device/port handles. Only that loop mutates physical state. A disconnect resets the pipeline and drops any pending gesture. The chord map, voicing templates, and strum preset will be read-only snapshots during a performance. The current pipeline uses no pygame objects or MIDI library and does not sleep.

Use one process and one control loop at first. No message broker, plugin framework, database, or network API is needed. If timing measurements show that polling plus MIDI sending is insufficient, add a dedicated scheduler thread behind the same interface. That is a measured optimization, not a starting assumption.

## Timing and strumming model

Use a monotonic clock for input receipt and scheduling. The current raw events and gestures carry `time.perf_counter()` seconds; a future scheduler may convert to integer nanoseconds at its boundary. Wall-clock time is useful only in logs. Each accepted gesture retains its horizontal-acquisition timestamp. The later planner computes each selected string's deadline as `gesture_time + offset`; it must not sleep inside input handling. The runtime will poll input frequently and drain due events. Python on a normal Windows desktop does not provide hard real-time guarantees.

The first future strum preset can be fixed and intentionally modest: six strings, a small constant gap between notes, fixed velocity, and a finite note length. The assignment of LEFT/RIGHT to bass-to-treble or treble-to-bass musical order remains configurable; the physical directions themselves do not imply downstroke/upstroke. For the E-major example, one order is `E2 B2 E3 G#3 B3 E4` and the reverse is `E4 B3 G#3 E3 B2 E2`. Exclude muted strings before assigning offsets so there are no unexplained silent gaps.

The `StrumPreset` is the future extension point for direction-specific string coverage, gap or overall duration, overall velocity, per-string velocity curve, and articulation. A natural preset may make downstrokes cover more bass strings and upstrokes favor treble strings. These controls modify a planner, not the Titan profile or MIDI transport. The first version should have one or two presets, not a general rule language.

The verified gesture rule is **x=0 -> x=-1 or +1**. x=-1 is LEFT, x=+1 is RIGHT. A held side cannot retrigger; x must return to 0 to re-arm. y need not return to 0: UP -> UP+LEFT -> UP -> UP+RIGHT yields repeated STRICT strokes, while the corresponding DOWN sequence yields FULL strokes. y=-1 means FULL, y=0 NORMAL, and y=+1 STRICT. Vertical-only transitions produce no stroke. FULL/NORMAL/STRICT are semantic values; no velocity or coverage behavior is assigned yet.

Real SDL traces can report an intermediate cardinal before a diagonal, such as CENTER -> LEFT -> UP+LEFT or CENTER -> DOWN -> DOWN+LEFT. The recognizer therefore holds a new horizontal acquisition for a configurable **8 ms** settle window. A nonzero y seen on the same horizontal side in that window refines its character; later y=0 does not erase a diagonal already seen. `flush(now)` emits a settled gesture even if no further input arrives, and a quick horizontal return to x=0 emits it immediately. The timestamp and immutable fingering are captured at the initial horizontal acquisition. This delay belongs entirely to the input/gesture layer and can be tuned from measured playing latency; it never creates a second gesture for one excursion.

Each note-on must have a matching note-off. The scheduler tracks active `(channel, pitch)` notes and scheduled releases. On a retrigger of the same pitch, send its prior note-off immediately before the new note-on, then replace its pending release; this avoids an old release cutting off the new note. On disconnect, output error, profile reload, or normal shutdown, cancel pending note-ons and release active notes on the selected channel. Prefer explicit note-offs; an all-notes-off control change can be a backup. The first version uses MIDI 1.0 note messages on one configurable channel, with no per-string pitch bend or MPE.

## MIDI output and Windows integration

`MidoRtMidiOutput` should enumerate output ports, open a configured existing port by exact name, send MIDI 1.0 messages, and surface disconnect/errors to the runtime. Do not silently fall back to a different MIDI port. Include a diagnostic command that lists available outputs and sends a short test note. The runtime reports a missing port and retries opening it on a controlled interval; musical state resets during an outage.

For the prototype, a third-party virtual MIDI loopback provides the DAW-visible **Vega Guitar** endpoint. It is an installation/setup dependency, not a Python module. Verify the actual port name and routing in at least one DAW. The later native-endpoint option belongs behind `MidiOutput` plus an endpoint lifecycle adapter; evaluate Windows MIDI Services only after the playable path works. Direct endpoint publication may require a helper outside Python and has different installation and lifecycle requirements.

## Background runtime and future configuration

The runtime is a normal long-running foreground process for early development, with a console status line or logs. Later package it for background launch at user login if needed. It should:

1. Load and validate the Titan profile, fingering map, strum preset, and MIDI port/channel settings.
2. Initialize pygame's joystick subsystem, find the selected Titan, and start pumping events.
3. Open the configured MIDI output and enter the poll/schedule loop.
4. Report device/port connection state, accepted gestures, and errors without logging every event during normal play.
5. On Titan disconnect or process stop, cancel future notes and release active notes; on reconnect, start from a neutral physical state.

The future settings UI can edit configuration atomically and request a safe reload between gestures. Do not build a GUI or a background service before the input mapping and DAW path are proven. A single runtime instance should own the controller and MIDI output; a second instance should fail clearly rather than create duplicate notes.

## Testing strategy

- **Implemented input tests:** table-test all eight PC+DP face mappings, axis startup/calibration and release, simultaneous held faces, nine hat positions, horizontal re-arm, vertical-only silence, diagonal transition orders, gesture timing, fingering snapshots, and reset. Inject timestamps; use no sleeps or physical controller.
- **Future musical unit tests:** table-test known and unknown fingerings, interval interpretation, voicing order/pitches, muted strings, chosen LEFT/RIGHT string ordering, coverage, velocity limits, and note-off pairing. Test the E-major example exactly.
- **Future deterministic MIDI timing tests:** inject a fake monotonic clock and fake MIDI sink. Assert computed deadlines, event ordering for equal deadlines, late wake behavior, retrigger note-off order, and shutdown cleanup without real sleeps.
- **Hardware tests:** PC+DP mapping is verified. Confirm the pipeline's 8 ms diagonal window and concurrent game-controller access with the real Titan; map LS and RS separately if needed. Measure gesture-to-first-note latency and inter-string gaps once MIDI exists.
- **DAW smoke test:** send test notes through the named port, select it in one DAW, verify audible notes, note-offs, and recovery after unplugging the Titan or losing the MIDI port. Expand DAW coverage later.

Keep raw traces and expected symbolic events as small fixtures. Do not write tests that depend on a live controller or installed DAW as part of the normal unit test run.

## Proposed repository structure

```text
ARCHITECTURE.md
README.md
pyproject.toml
src/vega/
  __main__.py          # command entry point
  runtime.py           # lifecycle and control loop
  model.py             # small shared enums/dataclasses
  input/
    events.py          # pygame-independent raw event records
    titan_profile.py   # verified PC+DP IDs and axis normalization
    state.py           # held faces and lever x/y
    pipeline.py        # translate, update state, recognize gestures
  music/
    strum.py           # implemented pure stroke recognizer
    fingering.py       # later: chord/interval interpretation
    voicing.py         # later: virtual strings and voicing templates
  midi/
    scheduler.py       # deadlines and active-note bookkeeping
    output.py          # Mido/RtMidi adapter
  diagnostics/
    inspect_titan.py   # first hardware probe; raw event logging
config/
  guitar.json          # later: fingering map, voicings, strum preset
tests/
  test_inspect_titan.py
  test_titan_profile.py
  test_strum.py
  test_fingering.py   # later
  test_voicing.py     # later
  test_scheduler.py   # later
```

This is a proposed destination, not a request to create every file immediately. Add modules as working slices need them. `model.py` should stay small; move a type beside its sole consumer if it has no cross-module use.

## Technical risks

| Risk | Practical response |
| --- | --- |
| Titan reports different IDs/joystick forms in other modes, or pygame does not observe it while a game uses it | PC+DP mapping is verified; keep LS/RS and other system modes separate; test concurrent access. Consider a different input adapter only if evidence requires it. |
| SDL background focus or hotplug behavior drops events | Keep pumping the event queue, test focus changes and reconnects, clear physical state on disconnect. |
| Windows virtual MIDI endpoint is absent or named differently | Enumerate ports, require explicit selection, document loopback setup, fail visibly. |
| Timing jitter makes strums uneven | Use absolute monotonic deadlines and measure latency; consider a separate scheduling thread only after profiling. |
| Hanging notes after errors or repeated same-pitch strokes | Track active notes and releases; panic on stop/disconnect; test retrigger ordering. |
| Chord mapping feels difficult to learn or voicings sound unnatural | Begin with a small documented vocabulary and explicit voicings; iterate from playing tests. |
| Python 3.13 package/driver compatibility varies by Windows installation | Pin tested versions after installing on the target machine; keep adapter boundaries so a library can be replaced. |

## Decisions stable now

- Python 3.13, Windows first, Titan first; pygame/SDL is the initial input adapter.
- Read the Titan while preserving ordinary controller behavior as a product requirement.
- Musical logic uses symbolic face and direction controls, never raw Titan IDs.
- Fingerings are snapshots of simultaneous held face buttons; a stroke triggers the snapshot.
- In PC+DP mode, horizontal x acquisition triggers LEFT/RIGHT; y modifies FULL/NORMAL/STRICT; only x=0 rearms.
- Axis 5 and axis 4 normalize to FACE_7 and FACE_8. Startup axis 0.0 is not a press.
- Chord meaning, guitar voicing, stroke recognition, strum planning, scheduling, and MIDI transport have distinct responsibilities, though not necessarily distinct classes.
- Six future virtual strings are ordered low to high. The LEFT/RIGHT to musical string-order assignment remains configurable.
- MIDI 1.0 notes through an existing Windows output port are the first transport; the DAW sees the matching loopback input named Vega Guitar.
- The runtime operates without a settings UI and has deterministic tests for its pure musical decisions.

## Decisions pending further hardware and playing tests

- Whether PC+DP input remains available while a game/controller tester has focus and whether all non-face controls should be mapped later.
- Whether the 8 ms diagonal settle window feels right on hardware, including very quick taps, reversals, and focus changes.
- LS/RS lever mappings and other Titan system-switch modes, if support is needed.
- The musical string-order assignment for LEFT and RIGHT; how FULL and STRICT affect later coverage, timing, or velocity.
- Measured end-to-end latency, virtual-port setup, DAW routing, and whether a timing worker is justified.

## Staged implementation plan

1. **Titan discovery — done:** the standalone `inspect_titan.py` captured PC+DP observations; the verified findings above are sufficient for this stage. The diagnostic remains available for later modes.
2. **Symbolic input and gesture slice — done:** the PC+DP profile, physical state, and deterministic LEFT/RIGHT recognizer are implemented and tested without pygame in the musical layer.
3. **Next: musical slice:** implement a small fingering/chord vocabulary, explicit guitar voicings, virtual strings, and pure strum plans using `StrumGesture`. Decide LEFT/RIGHT musical ordering from playing tests.
4. **MIDI and DAW slice:** implement scheduler, Mido/RtMidi output to a configured loopback port, safe note cleanup, a test-note command, and one DAW smoke test.
5. **Playable runtime:** connect the pygame adapter to the input pipeline and MIDI path; handle startup, disconnects, errors, logs, and latency measurement. Refine the settle window from real playing.
6. **Usability and extension:** add configuration validation, more chord/voicing presets, directional dynamics, packaging/background launch, and only then a settings UI or native Windows endpoint if warranted.

## Beginner-friendly summary

Vega reads the Titan like a game controller. A small PC+DP profile gives each real button and joystick movement a symbolic name. The buttons you hold form a fingering. Moving the lever left or right starts one strum; holding it up makes that strum STRICT, holding it down makes it FULL, and leaving it vertically centered makes it NORMAL. Returning only the horizontal part to center prepares the next strum. Later, a guitar voicing will turn the fingering into string pitches and a scheduler will send them as MIDI to the DAW. Each part can be tested on its own.

## Main unresolved technical questions

1. Can pygame keep receiving PC+DP events while another application uses the Titan normally, including when Vega is not focused?
2. Does the 8 ms diagonal settle window feel right in real play, especially for fast taps and reversals?
3. Which musical string order should LEFT and RIGHT select, and what should FULL and STRICT eventually change?
4. Which loopback endpoint works reliably with the target DAW, and what timing does the full controller-to-sound path achieve?

## Completed input-stage boundary

`inspect_titan.py` stays a raw hardware diagnostic. `TitanPcDpProfile` alone owns measured pygame IDs and axis normalization; `PhysicalState` and `StrumRecognizer` know only symbolic controls. `VegaInputPipeline` connects them and exposes `on_raw(event)` plus `flush(now)` for a future runtime. This stage intentionally contains no chord vocabulary, voicing, virtual-string simulation, MIDI output, or GUI.

The live `inspect_gestures.py` diagnostic now uses a pygame input adapter to feed that same production pipeline. It prints symbolic state and finalized gestures, and calls `flush(now)` on every event-loop pass so an 8 ms pending stroke completes even when no further SDL event arrives. `--settle-ms` allows comparison on the real Titan; the window remains a playing-test decision. The older raw inspector remains separate for future hardware discovery.
