import numpy as np
from plugins import AudioPlugin

# Plugin que causa efeito de reverberacao do audio
# MGDegenhardt 2026

class ReverbPlugin(AudioPlugin):
    def __init__(self, room_size: float = 0.75, damping: float = 0.4, mix: float = 0.35, sample_rate: int = 44100):
        """
        ReverbPlugin - Um efeito de reverberação espacial baseado no modelo clássico de Schroeder.
        Combina múltiplos filtros Comb em paralelo para simular reflexões densas e
        filtros Allpass em série para aumentar a densidade de eco de forma natural.

        :param room_size: Tamanho da sala virtual (feedback dos filtros comb) - 0.0 a 0.95
        :param damping: Absorção de frequências agudas (coeficiente do filtro passa-baixas básico) - 0.0 a 1.0
        :param mix: Proporção entre o som limpo (dry) e o som reverberado (wet) - 0.0 a 1.0
        :param sample_rate: Taxa de amostragem padrão (44100 Hz)
        """
        super().__init__("Reverb")
        self.room_size = max(0.0, min(0.95, room_size))
        self.damping = max(0.0, min(1.0, damping))
        self.mix = max(0.0, min(1.0, mix))
        self.sample_rate = sample_rate

    def _comb_filter(self, wave: np.ndarray, delay_ms: float, feedback: float) -> np.ndarray:
        """Filtro Comb realimentado com atenuação (damping) opcional para simular perdas de parede."""
        delay_samples = int((delay_ms / 1000.0) * self.sample_rate)
        if delay_samples <= 0:
            return wave.copy()

        # Buffer estendido para conter a cauda acústica natural do reverb
        out_len = len(wave) + delay_samples * 8
        out = np.zeros(out_len, dtype=np.float32)
        out[:len(wave)] = wave

        # Simula o reflexo contínuo e atenuação física das altas frequências
        last_val = 0.0
        for i in range(len(wave)):
            if i + delay_samples < out_len:
                # Damping (filtro passa-baixas de 1 polo simples na realimentação)
                curr_val = out[i] * feedback
                damped_val = curr_val * (1.0 - self.damping) + last_val * self.damping
                last_val = damped_val
                out[i + delay_samples] += damped_val
        return out

    def _allpass_filter(self, wave: np.ndarray, delay_ms: float, feedback: float) -> np.ndarray:
        """Filtro Allpass para espalhar as fases e criar densidade de eco sem colorir o som."""
        delay_samples = int((delay_ms / 1000.0) * self.sample_rate)
        if delay_samples <= 0:
            return wave.copy()

        out = np.zeros_like(wave, dtype=np.float32)
        # Equação de diferença do Allpass: y[n] = -g * x[n] + x[n-d] + g * y[n-d]
        out[:len(wave)] = -feedback * wave
        for i in range(len(wave)):
            if i >= delay_samples:
                out[i] += wave[i - delay_samples] + feedback * out[i - delay_samples]
        return out

    def process(self, wave: np.ndarray) -> np.ndarray:
        if not self.enabled or len(wave) == 0:
            return wave

        # 1. Quatro Filtros Comb em paralelo com tempos de atraso primos entre si
        # Isso impede ressonâncias metálicas indesejadas na sala virtual
        c1 = self._comb_filter(wave, 29.7, self.room_size * 0.72)
        c2 = self._comb_filter(wave, 37.1, self.room_size * 0.75)
        c3 = self._comb_filter(wave, 41.1, self.room_size * 0.78)
        c4 = self._comb_filter(wave, 43.7, self.room_size * 0.81)

        # Soma e mixa as quatro reflexões paralelas
        max_len = max(len(c1), len(c2), len(c3), len(c4))
        comb_sum = np.zeros(max_len, dtype=np.float32)
        comb_sum[:len(c1)] += c1 * 0.25
        comb_sum[:len(c2)] += c2 * 0.25
        comb_sum[:len(c3)] += c3 * 0.25
        comb_sum[:len(c4)] += c4 * 0.25

        # 2. Passa a soma por dois Filtros Allpass em série para adensar o eco
        ap1 = self._allpass_filter(comb_sum, 5.0, 0.7)
        ap2 = self._allpass_filter(ap1, 1.7, 0.7)

        # Ajusta e corta para coincidir com o tamanho do loop original (evita assincronias)
        wet = ap2[:len(wave)]

        # Normaliza o volume do sinal de reverberação em relação ao sinal original
        peak_orig = np.max(np.abs(wave))
        peak_wet = np.max(np.abs(wet))
        if peak_wet > 0 and peak_orig > 0:
            wet = wet * (peak_orig / peak_wet) * 0.75

        # Retorna a mixagem entre o som original e o ambiente espacial
        return wave * (1.0 - self.mix) + wet * self.mix
