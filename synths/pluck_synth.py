import numpy as np
from base_synth import BaseSynthesizer

# Sintetizador pluck basico
# MGDegenhardt, 2026 - OndaKraft

class PluckSynth(BaseSynthesizer):
    def __init__(self):
        """Sintetizador percussivo ideal para notas curtas e timbres de cordas dedilhadas."""
        super().__init__("PLUCK")

    def generate_wave(self, freq: float, duration: float, sample_rate: int = 44100,
                      velocity: float = 1.0) -> np.ndarray:
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        # Ataque rápido e brilhante
        wave = np.sin(2 * np.pi * freq * t) * 0.65
        wave += np.sin(2 * np.pi * freq * 2.0 * t) * 0.25

        fade = np.exp(-14.0 * t)  # Decaimento ultra-rápido (pluck)
        attack = np.minimum(1.0, t / 0.002)  # Ataque extremamente rápido de 2ms
        return wave * fade * attack * 0.65 * velocity