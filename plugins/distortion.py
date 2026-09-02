import numpy as np
from plugins import AudioPlugin

# Plugin que causa efeito de distorcao do audio
# MGDegenhardt 2026

class DistortionPlugin(AudioPlugin):
    def __init__(self, drive: float = 8.0, mix: float = 0.6):
        super().__init__("Distortion")
        self.drive = max(1.0, drive)
        self.mix = max(0.0, min(1.0, mix))

    def process(self, wave: np.ndarray) -> np.ndarray:
        if not self.enabled or len(wave) == 0:
            return wave
        distorted = np.tanh(wave * self.drive) # Soft-clipping
        peak_orig = np.max(np.abs(wave))
        peak_dist = np.max(np.abs(distorted))
        if peak_dist > 0 and peak_orig > 0:
            distorted = distorted * (peak_orig / peak_dist) # Normaliza o volume
        return wave * (1.0 - self.mix) + distorted * self.mix