import numpy as np
from plugins import AudioPlugin

# Plugin para dimiuicao entre pontos máximos e minimos de audio
# MGDegenhardt 2026

class CompressorPlugin(AudioPlugin):
    def __init__(self, threshold: float = -12.0, ratio: float = 4.0,
                 attack: float = 0.010, release: float = 0.100,
                 makeup_gain: float = 1.5, sample_rate: int = 44100):
        """
        Compressor de Dinâmica de Áudio para o OndaKraft.
        Reduz a faixa dinâmica do sinal atenuando picos que ultrapassam o 'threshold'
        e compensa a perda de volume com o 'makeup_gain'.

        :param threshold: Limiar em decibéis (dB) acima do qual a compressão é aplicada (ex: -12.0)
        :param ratio: Razão de compressão (ex: 4.0 significa 4:1)
        :param attack: Tempo de ataque em segundos (quão rápido o compressor reage)
        :param release: Tempo de liberação em segundos (quão rápido ele solta o ganho)
        :param makeup_gain: Ganho de compensação linear para recuperar o volume (ex: 1.5)
        """
        super().__init__("Compressor")
        self.threshold_db = threshold
        self.ratio = max(1.0, ratio)
        self.attack = max(0.001, attack)
        self.release = max(0.010, release)
        self.makeup_gain = max(0.0, makeup_gain)
        self.sample_rate = sample_rate

    def process(self, wave: np.ndarray) -> np.ndarray:
        if not self.enabled or len(wave) == 0:
            return wave

        # Converte o limite de dB para amplitude linear (ex: 0dB = 1.0, -6dB = 0.5, etc.)
        threshold_linear = 10 ** (self.threshold_db / 20.0)

        # Coeficientes de filtro para o detector de envelope baseados nos tempos de Attack e Release
        g_attack = np.exp(-1.0 / (self.attack * self.sample_rate))
        g_release = np.exp(-1.0 / (self.release * self.sample_rate))

        # Aloca um vetor para armazenar o envelope de amplitude e o ganho
        envelope = 0.0
        gain_reduction = np.ones(len(wave), dtype=np.float32)

        # Loop do detector de envelope (feedforward)
        for i in range(len(wave)):
            input_level = abs(wave[i])

            # Seguidor de envelope com tempos de subida (attack) e descida (release)
            if input_level > envelope:
                envelope = g_attack * envelope + (1.0 - g_attack) * input_level
            else:
                envelope = g_release * envelope + (1.0 - g_release) * input_level

            # Se o envelope passar do limiar (threshold), calcula a atenuação
            if envelope > threshold_linear and envelope > 0:
                # Equação padrão de compressão linear:
                # desired_level = threshold + (envelope - threshold) / ratio
                desired_level = threshold_linear + (envelope - threshold_linear) / self.ratio
                gain_reduction[i] = desired_level / envelope
            else:
                gain_reduction[i] = 1.0

        # Aplica a redução de ganho dinâmica e compensa com o ganho de saída (makeup)
        compressed_wave = wave * gain_reduction * self.makeup_gain
        return compressed_wave
