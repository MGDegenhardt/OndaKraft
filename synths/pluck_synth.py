import numpy as np
from base_synth import BaseSynthesizer

# Sintetizador pluck basico
# MGDegenhardt, 2026 - OndaKraft

class PluckSynth(BaseSynthesizer):
    def __init__(self):
        """Sintetizador percussivo ideal para notas curtas e timbres de cordas dedilhadas."""
        super().__init__("PLUCK")
        self.parameters = {
            "Decaimento (Release)": [14.0, 4.0, 40.0],
            "Brilho Metal (Sinos)": [0.25, 0.0, 1.0]
        }

    def generate_wave(self, freq: float, duration: float, sample_rate: int = 44100,
                      velocity: float = 1.0) -> np.ndarray:
        decay = self.parameters["Decaimento (Release)"][0]
        metal = self.parameters["Brilho Metal (Sinos)"][0]

        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        # Ataque rápido e brilhante
        wave = np.sin(2 * np.pi * freq * t) * (1.0 - metal * 0.3)
        wave += np.sin(2 * np.pi * freq * 2.0 * t) * metal * 0.3
        wave += np.sin(2 * np.pi * freq * 5.51 * t) * metal * 0.2

        fade = np.exp(-decay * t)  # Decaimento controlado
        attack = np.minimum(1.0, t / 0.002)  # Ataque extremamente rápido de 2ms
        return wave * fade * attack * 0.65 * velocity
