"""Prebuilt triangle notes on SDL channels; shared-plan offsets, no harmony."""

import heapq

from vega.audio.preview import MAX_PREVIEW_VOICES, render_note
from vega.music.plan import PROFILES, StrumPlan


class PygameAudioBackend:
    def initialize(self) -> None:
        import pygame

        self.mixer = pygame.mixer
        self.mixer.init(frequency=44100, size=-16, channels=1, buffer=256, allowedchanges=0)
        self.mixer.set_num_channels(MAX_PREVIEW_VOICES * 6)
        # All possible MIDI pitches: no waveform generation during live input.
        self.sounds = {(pitch, p.duration): self.mixer.Sound(buffer=render_note(pitch, p.duration))
                       for pitch in range(128) for p in PROFILES.values()}
        self.queue = []
        self.generation = 0
        self.groups = [0] * MAX_PREVIEW_VOICES
        self.volume = 0.65
        self.channel_velocity = [1.0] * (MAX_PREVIEW_VOICES * 6)

    def play(self, strum: StrumPlan, volume: float, now: float) -> None:
        self.volume = volume
        self.generation += 1
        group = (self.generation - 1) % MAX_PREVIEW_VOICES
        self.groups[group] = self.generation
        for i in range(6):
            self.mixer.Channel(group * 6 + i).stop()
        self.queue = [item for item in self.queue if item[2] != group]
        heapq.heapify(self.queue)
        for i, note in enumerate(strum.notes):
            heapq.heappush(self.queue, (now + note.offset, self.generation, group, i, note))

    def tick(self, now: float) -> None:
        while self.queue and self.queue[0][0] <= now:
            _, generation, group, index, note = heapq.heappop(self.queue)
            if self.groups[group] != generation:
                continue
            channel_index = group * 6 + index
            self.channel_velocity[channel_index] = note.velocity / 127
            channel = self.mixer.Channel(channel_index)
            channel.set_volume(self.volume * note.velocity / 127)
            channel.play(self.sounds[note.note, note.duration])

    def set_volume(self, volume: float) -> None:
        self.volume = volume
        for index, velocity in enumerate(self.channel_velocity):
            self.mixer.Channel(index).set_volume(volume * velocity)

    def stop(self) -> None:
        self.queue.clear()
        self.mixer.stop()

    def close(self) -> None:
        mixer = getattr(self, "mixer", None)
        if mixer is not None and mixer.get_init():
            if hasattr(self, "queue"):
                self.queue.clear()
            mixer.stop()
            mixer.quit()
        # Release PCM even if another SDL owner already shut down the mixer.
        if hasattr(self, "queue"):
            self.queue.clear()
        if hasattr(self, "sounds"):
            self.sounds.clear()
