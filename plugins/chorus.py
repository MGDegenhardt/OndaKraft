import numpy as np
from plugins import AudioPlugin

# Plugin para simulacao de coro no audio
# MGDegenhardt 2026

class ChorusPlugin(AudioPlugin):
    def __init__(self, delay_ms: float = 30.0, depth_ms: float = 3.0, rate: float = 1.5, mix: float = 0.5,
                 sample_rate: int = 44100):
        """
        ChorusPlugin - Cria o efeito de "coro" clássico de estúdio.
        Duplica o sinal de áudio, atrasa a cópia sutilmente (20ms-40ms) e modula
        esse atraso no tempo usando um Oscilador de Baixa Frequência (LFO) senoidal.
        A mistura resultante simula vários instrumentos ou vozes tocando em uníssono.

        :param delay_ms: Tempo médio de atraso em milissegundos (padrão: 30.0ms)
        :param depth_ms: Amplitude máxima de modulação de atraso em milissegundos (padrão: 3.0ms)
        :param rate: Frequência de modulação do LFO em Hertz (padrão: 1.5Hz)
        :param mix: Equilíbrio entre o som original limpo (dry) e com efeito (wet) (padrão: 0.5)
        :param sample_rate: Taxa de amostragem padrão (44100 Hz)
        """
        super().__init__("Chorus")
        self.delay_ms = delay_ms
        self.depth_ms = depth_ms
        self.rate = rate
        self.mix = max(0.0, min(1.0, mix))
        self.sample_rate = sample_rate

    def process(self, wave: np.ndarray) -> np.ndarray:
        if not self.enabled or len(wave) == 0:
            return wave

        # Converte os tempos de ms para quantidade física de amostras (samples)
        base_delay_samples = (self.delay_ms / 1000.0) * self.sample_rate
        max_depth_samples = (self.depth_ms / 1000.0) * self.sample_rate

        # Garante limite mínimo seguro para evitar leituras de índices futuros
        if base_delay_samples - max_depth_samples < 1.0:
            base_delay_samples = max_depth_samples + 1.0

        n_samples = len(wave)

        # Cria vetor temporal contínuo baseado no sample_rate
        t = np.arange(n_samples) / self.sample_rate

        # Gera o LFO senoidal modulador
        lfo = np.sin(2 * np.pi * self.rate * t)

        # Calcula o mapa de atrasos dinâmicos e fracionários para cada amostra
        delay_map = base_delay_samples + max_depth_samples * lfo

        # Mapeia quais índices do passado devemos ler
        indices_dry = np.arange(n_samples)
        indices_wet = indices_dry - delay_map

        # Previne leituras fora do array (out of bounds)
        indices_wet_clipped = np.clip(indices_wet, 0, n_samples - 1)

        # Interpolação Linear Fracionária (evita ruídos digitais de "escada")
        indices_floor = np.floor(indices_wet_clipped).astype(np.int32)
        indices_ceil = np.minimum(indices_floor + 1, n_samples - 1)
        frac = indices_wet_clipped - indices_floor

        # Reconstrói a onda atrasada e modulada combinando as amostras vizinhas
        wet_wave = (1.0 - frac) * wave[indices_floor] + frac * wave[indices_ceil]

        # Qualquer leitura que resulte em índice negativo (antes do início do som) é silenciada
        wet_wave = np.where(indices_wet >= 0, wet_wave, 0.0)

        # Soma o som original seco (dry) e com efeito (wet) baseado no fader de Mix
        output = wave * (1.0 - self.mix) + wet_wave * self.mix
        return output
