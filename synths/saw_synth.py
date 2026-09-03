import numpy as np
from base_synth import BaseSynthesizer

# Sintetizador de dois dentes de serra
# MGDegenhardt, 2026 - OndaKraft

class SawSynth(BaseSynthesizer):
    def __init__(self):
        """
        SawSynth - Sintetizador Subtrativo Analógico (Warm Unison Saw).
        Simula o som clássico de sintetizadores vintage dos anos 80, com duas dentes-de-serra desafinadas,
        passando por um filtro passa-baixas espectral dinâmico e saturação analógica.
        """
        super().__init__("SAW")
        # Parâmetros customizáveis via janela de moldar timbre: [atual, min, max]
        self.parameters = {
            "Abertura Filtro (Cutoff Hz)": [1800.0, 150.0, 8000.0],
            "Saturacao (Drive)": [2.2, 1.0, 5.0],
            "Desafinacao (Detune Hz)": [1.5, 0.2, 8.0],
            "Volume Global": [0.55, 0.1, 1.0]
        }

    def generate_wave(self, freq: float, duration: float, sample_rate: int = 44100,
                      velocity: float = 1.0) -> np.ndarray:
        cutoff = self.parameters["Abertura Filtro (Cutoff Hz)"][0]
        drive = self.parameters["Saturacao (Drive)"][0]
        detune = self.parameters["Desafinacao (Detune Hz)"][0]
        volume = self.parameters["Volume Global"][0]

        total_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, total_samples, endpoint=False)

        # Gera duas ondas dentes-de-serra ligeiramente desafinadas para criar um coro analógico gordo (uníssono)
        saw1 = np.mod(t * (freq - detune), 1.0) * 2.0 - 1.0
        saw2 = np.mod(t * (freq + detune), 1.0) * 2.0 - 1.0
        wave = (saw1 + saw2) * 0.5

        # Filtro Passa-Baixas Espectral por Transformada Rápida de Fourier (FFT)
        spectrum = np.fft.rfft(wave)
        frequencies = np.fft.rfftfreq(total_samples, 1.0 / sample_rate)

        # Curva de filtragem passa-baixas de 4ª ordem (suave e sem cliques de fase)
        filter_shape = 1.0 / np.sqrt(1.0 + (frequencies / max(1.0, cutoff)) ** 4)
        spectrum *= filter_shape

        # Reconstrói a onda filtrada de volta para o domínio do tempo
        filtered_wave = np.fft.irfft(spectrum, n=total_samples)

        # Aplica saturação de ganho de fita usando tangente hiperbólica (np.tanh)
        saturated_wave = np.tanh(filtered_wave * drive)

        # Envelopes de Amplitude
        fade = np.exp(-4.5 * t)  # Decaimento médio de sintetizador analógico
        attack = np.minimum(1.0, t / 0.008)  # Ataque analógico rápido de 8ms

        return saturated_wave * fade * attack * volume * velocity
