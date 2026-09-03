import numpy as np
from base_synth import BaseSynthesizer

# Sintetizador bass basico
# MGDegenhardt, 2026 - OndaKraft

class BassSynth(BaseSynthesizer):
    def __init__(self):
        """Sintetizador sub-bass focado em frequências baixas e subgraves encorpados."""
        super().__init__("BASS")
        self.parameters = {
            "Saturação (Growl)": [0.0, 0.0, 1.0],
            "Peso Sub-Bass": [0.80, 0.20, 1.50]
        }

    def generate_wave(self, freq: float, duration: float, sample_rate: int = 44100,
                      velocity: float = 1.0) -> np.ndarray:
        saturacao = self.parameters["Saturação (Growl)"][0]
        peso = self.parameters["Peso Sub-Bass"][0]

        # Desce uma oitava inteira para peso de sub-bass
        bass_freq = freq / 2.0
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

        # Onda senoidal rica com harmônico grave quente
        wave = np.sin(2 * np.pi * bass_freq * t) * peso
        wave += np.sin(2 * np.pi * bass_freq * 2.0 * t) * 0.12

        # Aplica distorção harmônica quente np.tanh baseada na Saturação
        if saturacao > 0.0:
            drive = 1.0 + saturacao * 4.0
            wave = np.tanh(wave * drive) / (1.0 + saturacao * 0.5)

        fade = np.exp(-6.0 * t)
        attack = np.minimum(1.0, t / 0.015)  # Ataque macio de 15ms
        return wave * fade * attack * 0.65 * velocity
