import numpy as np
from plugins import AudioPlugin


    # Desenvolvimento da secao do mixer para o processamento de sinal
    # MGDegenhardt, 2026 - OndaKraft (baseado no JRYBeats)

class MixerChannel:
    def __init__(self, name: str, volume: float = 1.0, pan: float = 0.0):
        """
        Canal de mixer individual para controle e processamento de efeitos de uma trilha.
        """
        self.name = name
        self.volume = max(0.0, min(1.0, volume))
        self.pan = max(-1.0, min(1.0, pan))
        self.muted = False
        self.solo = False
        self.effects_chain: list[AudioPlugin] = []

    def add_plugin(self, plugin: AudioPlugin):
        """Adiciona um plugin de efeito à cadeia de processamento."""
        self.effects_chain.append(plugin)

    def remove_plugin(self, plugin_name: str):
        """Remove um plugin da cadeia pelo seu nome."""
        self.effects_chain = [p for p in self.effects_chain if p.name != plugin_name]

    def pan_to_lr(self) -> tuple[float, float]:
        """
        Calcula o ganho de volume para as caixas esquerda (L) e direita (R).
        Garante que o som se mova no espaço estéreo baseado no valor de panning [3].
        """
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
        """
        Determina se a trilha deve soar ou ser silenciada com base nos estados
        de Mute e Solo globais da DAW [3].
        """
        if self.muted:
            return False

        # Se qualquer canal do mixer estiver em SOLO, apenas os canais em SOLO tocam [3]
        any_solo = any(ch.solo for ch in all_channels)
        if any_solo:
            return self.solo

        return True

    def process_audio(self, wave: np.ndarray) -> np.ndarray:
        """
        Passa a onda gerada sequencialmente por todos os plugins ativos na trilha.
        """
        processed = wave.copy()
        for plugin in self.effects_chain:
            if plugin.enabled:
                processed = plugin.process(processed)
        return processed