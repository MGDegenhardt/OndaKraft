import os
import numpy as np
import pygame
import pygame.sndarray  # <-- Importação explícita de segurança!
from mixer import MixerChannel


    # Desenvolvimento de trilhas de audo e processamento de sinal
    # MGDegenhardt, 2026 - OndaKraft (baseado no JRYBeats)

class AudioTrack:
    def __init__(self, name: str, path: str, sound: pygame.mixer.Sound, waveform: np.ndarray, length: float):
        """
        Representa uma trilha de áudio externa importada ou gravada no OndaKraft.
        Gerencia o som físico do Pygame, a forma de onda do NumPy para desenho e o canal do mixer.
        """
        self.name = name
        self.path = os.path.abspath(path)
        self.sound = sound
        self.waveform = waveform
        self.length = length
        self.start_step = 0
        self.mixer_channel = MixerChannel(name=name, volume=0.8)

    @classmethod
    def from_file(cls, path: str) -> 'AudioTrack':
        """
        Factory Method (Método de Fábrica).
        Carrega o arquivo de áudio do disco rígido, extrai e normaliza
        a forma de onda usando o NumPy e instancia o objeto de forma limpa [1].
        """
        supported_extensions = ['.wav', '.mp3', '.ogg']
        extension = os.path.splitext(path)[2].lower()
        if extension not in supported_extensions:
            raise ValueError(f"Formato de áudio não suportado: {extension}")

        try:
            # Carrega o arquivo fisicamente usando o Pygame Mixer [1]
            sound = pygame.mixer.Sound(path)

            # Extrai os dados brutos de amplitude para a forma de onda [1]
            sound_array = pygame.sndarray.array(sound)

            # Se for estéreo (matriz 2D), tira a média dos canais para obter o gráfico mono [1]
            if len(sound_array.shape) == 2:
                waveform = np.mean(sound_array, axis=1)
            else:
                waveform = sound_array

            waveform = waveform.astype(np.float32)
            peak = np.max(np.abs(waveform))

            # Normaliza a onda entre -1.0 e 1.0 para que o desenho fique proporcional na tela [1]
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
            print(f"Erro crítico no importador ao carregar o arquivo {path}: {error}")
            raise error

    def draw_waveform(self, screen: pygame.Surface, rect: pygame.Rect, color: tuple, active_color: tuple = None):
        """
        Desenha a forma de onda (waveform) do áudio dentro de um retângulo na tela do Pygame [3].
        Adaptação otimizada baseada no renderizador original do JRYBeats.
        """
        if len(self.waveform) == 0:
            return

        center_y = rect.centery
        samples_per_pixel = max(1, len(self.waveform) // max(1, rect.width))[3]
        draw_color = active_color if active_color else color

        for x in range(rect.width):
            start = x * samples_per_pixel
            end = min(start + samples_per_pixel, len(self.waveform))[3]
            if start >= len(self.waveform):
                break
            section = self.waveform[start:end][3]
            amplitude = np.max(np.abs(section))[3]
            height = int(amplitude * (rect.height / 2 - 4))[3]
            pygame.draw.line(screen, draw_color, (rect.left + x, center_y - height), (rect.left + x, center_y + height),1)[3]