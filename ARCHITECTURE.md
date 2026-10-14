# Project Vega architecture

## Product definition

Project Vega is a Windows-first, Python 3.13 application that reads a Qanba Titan arcade fight stick and turns performance gestures into MIDI for a DAW. The Titan remains usable as a normal game controller: Vega reads its controller events and does not remap, suppress, or replace them. Whether simultaneous access works with the actual Titan mode, driver, and games must be verified on hardware.

The first instrument is **Vega Guitar**. Eight face buttons represent a held fingering. The joystick represents the picking hand. A recognized joystick stroke captures the current fingering, resolves its harmony, chooses a six-string guitar voicing, and schedules ordered MIDI notes. The DAW receives MIDI; a VST or other software instrument produces sound. Vega itself is not an audio engine or a guitar sample library.

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
| Input adapter | Read SDL/pygame events for one selected Titan; identify raw controls and connection changes | pygame, device IDs, raw axes/hats/buttons |
| Musical engine | Maintain physical state; recognize fingerings and strokes; resolve harmony and voicing; plan timed notes | symbolic controls, pitch, time; no pygame or MIDI library |
| Output/runtime | Deliver scheduled MIDI events, manage port and lifecycle, report errors | Mido/RtMidi, monotonic clock, configuration |

The logical flow is:

```text
Titan -> pygame/SDL -> raw events -> Titan profile -> symbolic controls
                                                   |
                                                   v
                                          current physical state
                                          /                    \
                                held fingering          stick movement
                                      |                       |
                            chord/interval model       stroke recognizer
                                      |                       |
                               guitar voicing -----> strum planner
                                (six strings)           (timed notes)
                                                           |
                                                   MIDI event scheduler
                                                           |
                                              MIDI output adapter -> DAW
```

This is a dependency diagram, not a mandate for one Python class per box. The fingering and gesture branches meet when a stroke is recognized. At that instant, the runtime takes a snapshot of the held fingering; subsequent button changes affect the next stroke, not already scheduled notes.

## Components and responsibilities

| Component | Input | Output / owned responsibility |
| --- | --- | --- |
| `PygameTitanInput` | pygame joystick queue | Raw button, hat, and axis events with device instance ID and receive time; connect/disconnect signals. Pump the SDL queue regularly. |
| `TitanProfile` | Raw control ID and value | Symbolic `FACE_1` through `FACE_8`, `STRUM_UP`, `STRUM_DOWN`, `STICK_NEUTRAL`, or `UNKNOWN`. This is data determined by hardware tests, not baked into music logic. |
| `PhysicalState` | Symbolic press/release and stick changes | Currently held face controls and stable stick direction. Updates are atomic within the single runtime loop. |
| `Fingering` | Snapshot of held face controls | Immutable set or 8-bit mask of controls; does not claim a specific chord until interpreted. |
| `FingeringInterpreter` | Fingering and active mapping | A harmonic choice such as root E and major triad intervals; unsupported fingerings return `None` with no new notes. |
| `Chord` / `Intervals` | Root pitch class and interval tuple | Pitch-independent harmonic meaning, e.g. major `(0, 4, 7)`; optional bass/inversion hint. |
| `GuitarVoicer` | Chord and voicing preset | Ordered six-string snapshot: one MIDI pitch or mute per virtual string. The initial voicer uses explicit, reviewed templates for supported chords rather than a complex fingering solver. |
| `VirtualString` | String ID, pitch, mute flag | A musical lane for ordering and coverage. It does not read hardware or send MIDI. |
| `StrokeRecognizer` | Stick state transitions and timestamps | One `StrumGesture` per accepted stroke, including direction and trigger time; filters repeats and accidental transitions. The exact trigger rules await Titan testing. |
| `StrumPlanner` | Gesture, voicing snapshot, strum preset | Ordered, absolute-deadline note-on and note-off intentions with chosen velocity and coverage. Pure logic. |
| `MidiScheduler` | Planned events and monotonic time | Due events in a small priority queue; handles cancellation and active-note bookkeeping without blocking input polling. |
| `MidiOutput` | Semantic note-on, note-off, panic | Opens an existing named MIDI output port and sends messages. A fake implementation supports tests. |
| `VegaRuntime` | Adapters, config, clock | Starts and stops components, connects the selected device/port, owns the loop, and coordinates recovery. |

The future settings interface edits validated configuration and displays status. It is a separate process or thin client of the background runtime, never the owner of the input loop or active notes. Start without a GUI; a configuration file and readable logs are enough for the prototype.

## Data flow and important data structures

Use small frozen dataclasses and enums in the engine. For example:

```text
RawInputEvent(device_instance_id, kind, control_id, value, received_at_ns)
ControlEvent(control, action, received_at_ns)
PhysicalState(held_faces, stick_direction)
Fingering(faces: frozenset[FaceControl])
Chord(root_pitch_class, intervals, bass_hint=None)
VirtualString(id, open_pitch, sounding_pitch: int | None)
Voicing(strings: tuple[VirtualString, ...])  # low string to high string
StrumGesture(direction, started_at_ns)
PlannedMidiEvent(due_at_ns, order, kind, channel, pitch, velocity, string_id)
```

The `TitanProfile` stores a device selector and raw-to-symbolic mappings in versioned data, such as JSON. A measured axis threshold, hysteresis, or hat mapping belongs there. Keep one symbolic name per physical face position. The profile must record the Titan's selected input mode and identifying fields (for example, name/GUID) because mappings can change by mode or driver. Runtime instance IDs identify the currently connected device; they are not persisted as profile IDs. Pygame documents event pumping, device-added/removed events, and instance IDs [pygame joystick documentation](https://www.pygame.org/docs/ref/joystick.html).

The initial fingering map is explicit: a defined face-control set maps to a `Chord` (and optionally a voicing preset). An empty or unrecognized set has a documented behavior: no new strum; already sounding notes continue until their scheduled release. This is predictable and easy to test. Add richer interval rules only after actual playing reveals a need.

For the E-major example, one voicing snapshot is `(E2, B2, E3, G#3, B3, E4)` from lowest to highest virtual string. In MIDI note numbers (C4 = 60), that is `(40, 47, 52, 56, 59, 64)`. These are sounding pitches; the physical Titan buttons are not literal guitar frets or strings.

## Module boundaries and state ownership

Proposed interfaces are intentionally narrow:

```text
InputSource.poll() -> list[RawInputEvent]
Profile.translate(raw_event) -> ControlEvent | None
Engine.on_control(control_event) -> list[PlannedMidiEvent]
Scheduler.add(events); Scheduler.pop_due(now_ns) -> list[PlannedMidiEvent]
MidiOutput.send(event); MidiOutput.all_notes_off(); MidiOutput.close()
Clock.now_ns() -> int
```

The runtime loop owns `PhysicalState`, the stroke recognizer, the event scheduler, and the selected device/port handles. Only the runtime mutates them. The chord map, voicing templates, profile, and strum preset are read-only snapshots during a performance. The pure engine accepts inputs and returns plans; it does not sleep or call pygame/Mido.

Use one process and one control loop at first. No message broker, plugin framework, database, or network API is needed. If timing measurements show that polling plus MIDI sending is insufficient, add a dedicated scheduler thread behind the same interface. That is a measured optimization, not a starting assumption.

## Timing and strumming model

Use a monotonic nanosecond clock for input receipt and scheduling. Wall-clock time is useful only in logs. Each accepted gesture has one trigger timestamp. The planner computes each selected string's deadline as `gesture_time + offset`; it never calls `sleep`. The runtime polls input frequently and drains all MIDI events due at the current clock reading. If the host wakes late, emit due events in deadline order and record lateness for diagnosis. Do not pretend Python on a normal Windows desktop provides hard real-time guarantees.

The first strum preset can be fixed and intentionally modest: six strings, a small constant gap between notes, fixed velocity, and a finite note length. The values are configuration, not embedded in input handling. A downstroke traverses low to high; an upstroke traverses high to low. Thus the E-major example yields `E2 B2 E3 G#3 B3 E4` down and the reverse up. Exclude muted strings before assigning offsets so there are no unexplained silent gaps.

The `StrumPreset` is the future extension point for direction-specific string coverage, gap or overall duration, overall velocity, per-string velocity curve, and articulation. A natural preset may make downstrokes cover more bass strings and upstrokes favor treble strings. These controls modify a planner, not the Titan profile or MIDI transport. The first version should have one or two presets, not a general rule language.

The initial recognizer should accept one stroke per deliberate move from neutral into an up/down direction and require release or neutral before retriggering. That is a provisional policy: if the Titan reports hat changes, axes, diagonals, or transitions that make this uncomfortable, hardware traces decide the debounce and rearm rules. Capture the fingering at the accepted stroke, and retain the resulting voicing for every event in that strum.

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

- **Pure unit tests:** table-test known and unknown fingerings, interval interpretation, voicing order/pitches, muted strings, down/up ordering, coverage, velocity limits, and note-off pairing. Test the E-major example exactly.
- **Deterministic timing tests:** inject a fake monotonic clock and fake MIDI sink. Assert computed deadlines, event ordering for equal deadlines, late wake behavior, retrigger note-off order, and shutdown cleanup without real sleeps.
- **Profile translation tests:** replay recorded Titan raw-event traces into the profile and recognizer. Verify every face button, joystick direction/neutral, release, diagonals if present, and disconnect/reconnect.
- **Hardware tests:** first map the Titan in each relevant input mode; then confirm that Vega can read it while another application still sees ordinary controller input. Measure gesture-to-first-note latency and inter-string gaps on the target Windows machine.
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
    pygame_titan.py    # SDL/pygame adapter
    titan_profile.py   # load/validate/translate raw mappings
  music/
    fingering.py       # fingering map and chord/interval model
    voicing.py         # virtual strings and explicit voicing templates
    strum.py           # stroke recognition and pure strum planning
  midi/
    scheduler.py       # deadlines and active-note bookkeeping
    output.py          # Mido/RtMidi adapter
  diagnostics/
    inspect_titan.py   # first hardware probe; raw event logging
config/
  titan_profile.json   # populated from hardware measurements
  guitar.json          # fingering map, voicings, strum preset
tests/
  test_fingering.py
  test_voicing.py
  test_strum.py
  test_scheduler.py
  fixtures/            # captured Titan event traces
```

This is a proposed destination, not a request to create every file immediately. Add modules as working slices need them. `model.py` should stay small; move a type beside its sole consumer if it has no cross-module use.

## Technical risks

| Risk | Practical response |
| --- | --- |
| Titan reports different IDs/joystick forms in different modes, or pygame does not observe it while a game uses it | Start with a raw event probe; store mappings by measured device mode; test concurrent access. Consider a different input adapter only if evidence requires it. |
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
- Chord meaning, guitar voicing, stroke recognition, strum planning, scheduling, and MIDI transport have distinct responsibilities, though not necessarily distinct classes.
- Six virtual strings are ordered low to high; downstroke goes low to high and upstroke high to low.
- MIDI 1.0 notes through an existing Windows output port are the first transport; the DAW sees the matching loopback input named Vega Guitar.
- The runtime operates without a settings UI and has deterministic tests for its pure musical decisions.

## Decisions pending Titan hardware testing

- Which Titan mode and Windows/SDL device identity to support first; whether simultaneous game-controller access works in that mode.
- The raw IDs and physical positions of all eight face buttons, including whether releases are reported reliably.
- Whether joystick motion appears as hat events, axes, buttons, or a mixture; what neutral and diagonals look like.
- Axis thresholds/hysteresis, event repetition, bounce, focus behavior, and the comfortable stroke/rearm rule.
- Measured end-to-end latency and whether the one-loop scheduler needs a timing worker.
- The virtual-port setup and exact DAW routing validated on the target Windows installation.

## Staged implementation plan

1. **Titan discovery:** build `inspect_titan.py` to enumerate devices and timestamp raw SDL events. Record all button, stick, mode, focus, and reconnect behavior; produce a reviewed `titan_profile.json` and trace fixtures. This is the first coding task.
2. **Pure musical slice:** implement symbolic state, a small fingering map, E-major and a few other explicit voicings, stroke recognition from replayed traces, and deterministic strum plans. Add focused unit tests.
3. **MIDI and DAW slice:** implement scheduler, Mido/RtMidi output to a configured loopback port, safe note cleanup, a test-note command, and one DAW smoke test.
4. **Playable runtime:** connect the Titan adapter to the engine and MIDI path; handle startup, disconnects, errors, logs, and latency measurement. Refine profile and strum feel from real playing.
5. **Usability and extension:** add configuration validation, more chord/voicing presets, directional dynamics, packaging/background launch, and only then a settings UI or native Windows endpoint if warranted.

## Beginner-friendly summary

Vega reads the Titan like a game controller. A small profile gives each real button and joystick movement a musical name. The buttons you are holding choose a chord; moving the stick says when and which way to strum it. A guitar voicing turns that chord into six string pitches, and a scheduler sends the pitches one after another as MIDI. A separate MIDI port carries those messages into the DAW, where the chosen instrument makes the sound. Each part can be tested on its own.

## Main unresolved technical questions

1. What raw events does the Titan actually send for each face button, joystick direction, neutral position, and input mode?
2. Can pygame keep receiving those events while another application uses the Titan normally, including when Vega is not focused?
3. What joystick transition feels like one intentional strum, and what debounce/rearm rules prevent duplicates?
4. Which loopback endpoint works reliably with the target DAW, and what timing does the full controller-to-sound path achieve?

## Exact first implementation task

Create a small Python 3.13 `inspect_titan.py` command using pygame/SDL. It must enumerate connected joystick devices (name, GUID, instance ID, counts of buttons/axes/hats), timestamp and print every raw button/axis/hat event plus connect/disconnect events, and offer a way to save a session trace. With the physical Titan connected, exercise each of the eight face buttons individually, simultaneous button combinations, every joystick direction, neutral returns, diagonals, press/release, focus changes, unplug/replug, and each relevant Titan input mode. Label the observed raw controls by physical position in a reviewed `config/titan_profile.json`, save representative traces as test fixtures, and verify that a game/controller tester still receives ordinary Titan input at the same time. No chord logic or MIDI output is needed in this first task.
