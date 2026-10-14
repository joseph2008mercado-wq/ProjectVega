"""Cached audition tones on SDL's mixer thread. No musical interpretation."""

from vega.audio.preview import MAX_PREVIEW_VOICES, PreviewStrum, preview_strum, render_strum
from vega.model import StrumCharacter, StrumDirection


class PygameAudioBackend:
    def initialize(self) -> None:
        import pygame

        self.mixer = pygame.mixer
        self.mixer.init(frequency=44100, size=-16, channels=1, buffer=256, allowedchanges=0)
        self.mixer.set_num_channels(MAX_PREVIEW_VOICES)
        self.sounds = {
            (character, direction): self.mixer.Sound(buffer=render_strum(preview_strum(character, direction)))
            for character in StrumCharacter for direction in StrumDirection
        }

    def play(self, strum: PreviewStrum, volume: float) -> None:
        channel = self.mixer.find_channel(force=True)
        channel.set_volume(volume)
        channel.play(self.sounds[strum.character, strum.direction])

    def set_volume(self, volume: float) -> None:
        for index in range(self.mixer.get_num_channels()):
            self.mixer.Channel(index).set_volume(volume)

    def stop(self) -> None:
        self.mixer.stop()

    def close(self) -> None:
        mixer = getattr(self, "mixer", None)
        if mixer is not None and mixer.get_init():
            mixer.stop()
            mixer.quit()
