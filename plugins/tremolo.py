import numpy as np
from plugins import AudioPlugin

# Plugin que causa efeito de tremulacao no audio
# MGDegenhardt 2026

class TremoloPlugin(AudioPlugin):
    def __init__(self, rate: float = 6.0, depth: float = 0.65, sample_rate: int = 44100):
        super().__init__("Tremolo")
        self.rate = rate
        self.depth = max(0.0, min(1.0, depth))
        self.sample_rate = sample_rate

    def process(self, wave: np.ndarray) -> np.ndarray:
        if not self.enabled or len(wave) == 0:
            return wave
        t = np.arange(len(wave)) / self.sample_rate
        lfo = 1.0 - self.depth + self.depth * (0.5 * (np.sin(2 * np.pi * self.rate * t) + 1.0))
        return wave * lfo