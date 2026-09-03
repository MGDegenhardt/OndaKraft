import numpy as np
from base_synth import BaseSynthesizer

# Sintetizador bass basico
# MGDegenhardt, 2026 - OndaKraft

class BassSynth(BaseSynthesizer):
    def __init__(self):
        """Sintetizador sub-bass focado em frequências baixas e subgraves encorpados."""
        super().__init__("BASS")

    def generate_wave(self, freq: float, duration: float, sample_rate: int = 44100,
                      velocity: float = 1.0) -> np.ndarray:
        # Desce uma oitava inteira para peso de sub-bass
        bass_freq = freq / 2.0
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

        # Onda senoidal rica com harmônico grave quente
        wave = np.sin(2 * np.pi * bass_freq * t) * 0.80
        wave += np.sin(2 * np.pi * bass_freq * 2.0 * t) * 0.12

        fade = np.exp(-6.0 * t)
        attack = np.minimum(1.0, t / 0.015)  # Ataque macio de 15ms
        return wave * fade * attack * 0.65 * velocity