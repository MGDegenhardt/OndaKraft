import numpy as np
from plugins import AudioPlugin

# Plugin para equalizacao de audio
# MGDegenhardt 2026

class EQPlugin(AudioPlugin):
    def __init__(self, low_gain: float = 1.0, mid_gain: float = 1.0, high_gain: float = 1.0, sample_rate: int = 44100):
        """
        EQPlugin - Equalizador Espectral de 3 Bandas (Grave, Médio, Agudo) usando FFT.

        Permite esculpir o timbre de cada trilha alterando o ganho de faixas de frequência específicas.

        :param low_gain: Ganho das frequências baixas (< 250 Hz). Padrão: 1.0 (neutro), Faixa: 0.0 a 3.0.
        :param mid_gain: Ganho das frequências médias (250 Hz a 4000 Hz). Padrão: 1.0, Faixa: 0.0 a 3.0.
        :param high_gain: Ganho das frequências altas (> 4000 Hz). Padrão: 1.0, Faixa: 0.0 a 3.0.
        """
        super().__init__("EQ")
        self.low_gain = max(0.0, min(3.0, low_gain))
        self.mid_gain = max(0.0, min(3.0, mid_gain))
        self.high_gain = max(0.0, min(3.0, high_gain))
        self.sample_rate = sample_rate

    def process(self, wave: np.ndarray) -> np.ndarray:
        if not self.enabled or len(wave) == 0:
            return wave

        # Converte o áudio do domínio do tempo para o domínio da frequência usando FFT real (rFFT)
        spectrum = np.fft.rfft(wave)
        frequencies = np.fft.rfftfreq(len(wave), 1 / self.sample_rate)

        # Cria filtros de cruzamento (crossover) com transições suaves para evitar distorções de fase brutas
        # Banda de Graves (Low): transição suave centrada em 250 Hz com largura de 50 Hz
        low_mask = np.clip((250 - frequencies) / 50 + 0.5, 0.0, 1.0)

        # Banda de Agudos (High): transição suave centrada em 4000 Hz com largura de 1000 Hz
        high_mask = np.clip((frequencies - 4000) / 1000 + 0.5, 0.0, 1.0)

        # Banda de Médios (Mid): tudo que sobra entre o corte de grave e agudo
        mid_mask = 1.0 - (low_mask + high_mask)
        mid_mask = np.clip(mid_mask, 0.0, 1.0)

        # Combina os ganhos nas respectivas bandas de frequência
        eq_shape = (low_mask * self.low_gain) + (mid_mask * self.mid_gain) + (high_mask * self.high_gain)

        # Aplica a máscara de equalização no espectro de frequências
        spectrum *= eq_shape

        # Reconverte o espectro de volta ao domínio do tempo usando a iFFT (Inverse FFT)
        filtered_wave = np.fft.irfft(spectrum, n=len(wave))

        # Preserva o volume geral original de pico para evitar distorção acidental por ganho excessivo
        orig_peak = np.max(np.abs(wave))
        filt_peak = np.max(np.abs(filtered_wave))
        if filt_peak > 1.0 and orig_peak <= 1.0:
            filtered_wave /= filt_peak

        return filtered_wave
