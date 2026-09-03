import numpy as np
from base_synth import BaseSynthesizer

# Sintetizador soft basico
# MGDegenhardt, 2026 - OndaKraft

class SoftSynth(BaseSynthesizer):
    def __init__(self):
        """Sintetizador analógico virtual de ondas senoidais suaves com harmônicos harmônicos."""
        super().__init__("SOFT")

    def generate_wave(self, freq: float, duration: float, sample_rate: int = 44100,
                      velocity: float = 1.0) -> np.ndarray:
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        # Fundamental + 2º harmônico sutil
        wave = np.sin(2 * np.pi * freq * t) * 0.75
        wave += np.sin(2 * np.pi * freq * 2.0 * t) * 0.15

        fade = np.exp(-5.0 * t)
        attack = np.minimum(1.0, t / 0.01)  # Suavização do ataque
        return wave * fade * attack * 0.65 * velocity