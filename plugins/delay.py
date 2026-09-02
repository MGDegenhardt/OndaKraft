from plugin_base import AudioPlugin  # Nossa classe base
import numpy as np

# Plugin que causa efeito de delay do audio
# MGDegenhardt 2026

class ReverbSimples(AudioPlugin):
    def __init__(self):
        super().__init__("Reverb Externo")

    def process(self, wave: np.ndarray) -> np.ndarray:
        # A matemática do reverb dele aplicada ao array NumPy...
        return wave * 0.9