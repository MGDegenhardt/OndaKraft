import os
import numpy as np
import pygame
import pygame.sndarray  # <-- Importação explícita de segurança!
from mixer import MixerChannel


    # Desenvolvimento de trilhas de audo e processamento de sinal
    # MGDegenhardt, 2026 - OndaKraft (baseado no JRYBeats)

class AudioTrack:
    def __init__(self, name: str, path: str, sound: pygame.mixer.Sound, waveform: np.ndarray, length: float):
        self.name = name
        self.path = os.path.abspath(path)
        self.sound = sound
        self.waveform = waveform
        self.length = length
        self.start_step = 0
        self.mixer_channel = MixerChannel(name=name, volume=0.8)

    @classmethod
    def from_file(cls, path: str) -> 'AudioTrack':
        """Factory Method para carregar e normalizar clipes [10]."""
        supported_extensions = ['.wav', '.mp3', '.ogg']
        extension = os.path.splitext(path).lower()
        if extension not in supported_extensions:
            raise ValueError(f"Formato não suportado: {extension}")

        try:
            sound = pygame.mixer.Sound(path)
            sound_array = pygame.sndarray.array(sound)

            if len(sound_array.shape) == 2:
                waveform = np.mean(sound_array, axis=1)
            else:
                waveform = sound_array

            waveform = waveform.astype(np.float32)
            peak = np.max(np.abs(waveform))

            if peak > 0:
                waveform /= peak

            return cls(
                name=os.path.basename(path),
                path=path,
                sound=sound,
                waveform=waveform,
                length=sound.get_length()
            )
        except Exception as error:
            print(f"Erro ao carregar {path}: {error}")
            raise error

    def draw_waveform(self, screen: pygame.Surface, rect: pygame.Rect, color: tuple, active_color: tuple = None):
        """Desenha a waveform usando NumPy adaptada de forma otimizada [11]."""
        if len(self.waveform) == 0:
            return

        center_y = rect.centery
        samples_per_pixel = max(1, len(self.waveform) // max(1, rect.width))
        draw_color = active_color if active_color else color

        for x in range(rect.width):
            start = x * samples_per_pixel
            end = min(start + samples_per_pixel, len(self.waveform))
            if start >= len(self.waveform):
                break
            section = self.waveform[start:end]
            amplitude = np.max(np.abs(section))
            height = int(amplitude * (rect.height / 2 - 4))
            pygame.draw.line(screen, draw_color, (rect.left + x, center_y - height), (rect.left + x, center_y + height),
                             1)