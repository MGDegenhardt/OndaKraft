from abc import ABC, abstractmethod
import numpy as np


    # Desenvolvimento da secao dos plugins e efeitos de sinal
    # MGDegenhardt, 2026 - OndaKraft (baseado no JRYBeats)

class AudioPlugin(ABC):
    def __init__(self, name: str):
        self.name = name
        self.enabled = True

    @abstractmethod
    def process(self, wave: np.ndarray) -> np.ndarray:
        pass

class DelayPlugin(AudioPlugin):
    def __init__(self, delay_time: float = 0.25, feedback: float = 0.4, mix: float = 0.3, sample_rate: int = 44100):
        super().__init__("Delay")
        self.delay_time = delay_time
        self.feedback = feedback
        self.mix = mix
        self.sample_rate = sample_rate

    def process(self, wave: np.ndarray) -> np.ndarray:
        """Aplica eco por realimentação de buffer NumPy [14]."""
        if not self.enabled or len(wave) == 0:
            return wave

        delay_samples = int(self.delay_time * self.sample_rate)
        if delay_samples <= 0:
            return wave

        out_len = len(wave) + delay_samples * 4
        out_wave = np.zeros(out_len, dtype=np.float32)
        out_wave[:len(wave)] = wave

        for i in range(len(wave)):
            if i + delay_samples < out_len:
                out_wave[i + delay_samples] += out_wave[i] * self.feedback

        dry_len = len(wave)
        mixed = wave * (1.0 - self.mix) + out_wave[:dry_len] * self.mix
        return mixed