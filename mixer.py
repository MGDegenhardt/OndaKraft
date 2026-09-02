import numpy as np
from plugins import AudioPlugin


    # Desenvolvimento da secao do mixer para o processamento de sinal
    # MGDegenhardt, 2026 - OndaKraft (baseado no JRYBeats)

class MixerChannel:
    def __init__(self, name: str, volume: float = 1.0, pan: float = 0.0):
        self.name = name
        self.volume = max(0.0, min(1.0, volume))
        self.pan = max(-1.0, min(1.0, pan))
        self.muted = False
        self.solo = False
        self.effects_chain: list[AudioPlugin] = []

    def add_plugin(self, plugin: AudioPlugin):
        self.effects_chain.append(plugin)

    def remove_plugin(self, plugin_name: str):
        self.effects_chain = [p for p in self.effects_chain if p.name != plugin_name]

    def pan_to_lr(self) -> tuple[float, float]:
        """Calcula a atenuação L/R estéreo baseada no Panning físico [13]."""
        pan = max(-1.0, min(1.0, self.pan))
        volume = max(0.0, min(1.0, self.volume))
        if pan < 0:
            left = volume
            right = volume * (1.0 + pan)
        else:
            left = volume * (1.0 - pan)
            right = volume
        return (left, right)

    def is_audible(self, all_channels: list['MixerChannel']) -> bool:
        """Processa as lógicas globais de Mute e Solo [13]."""
        if self.muted:
            return False
        any_solo = any(ch.solo for ch in all_channels)
        if any_solo:
            return self.solo
        return True

    def process_audio(self, wave: np.ndarray) -> np.ndarray:
        processed = wave.copy()
        for plugin in self.effects_chain:
            if plugin.enabled:
                processed = plugin.process(processed)
        return processed