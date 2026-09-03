import numpy as np
from base_synth import BaseSynthesizer

# Sintetizador FM
# MGDegenhardt, 2026 - OndaKraft

class BellSynth(BaseSynthesizer):
    def __init__(self):
        """
        BellSynth - Sintetizador de Modulação de Frequência (FM) Clássico.
        Gera timbres inharmônicos de sinos, marimbas, metais brilhantes e piano elétrico vintage.
       """
        super().__init__("BELL")
        # Parâmetros customizáveis via janela de moldar timbre: [atual, min, max]
        self.parameters = {
            "Razao Moduladora (Ratio)": [2.767, 1.0, 8.0],
            "Brilho Metal (Mod Index)": [8.0, 0.0, 20.0],
            "Decaimento Metal (Mod Decay)": [12.0, 1.0, 30.0],
            "Volume Global": [0.65, 0.1, 1.0]
        }

    def generate_wave(self, freq: float, duration: float, sample_rate: int = 44100,
                      velocity: float = 1.0) -> np.ndarray:
        ratio = self.parameters["Razao Moduladora (Ratio)"][0]
        mod_index = self.parameters["Brilho Metal (Mod Index)"][0]
        mod_decay = self.parameters["Decaimento Metal (Mod Decay)"][0]
        volume = self.parameters["Volume Global"][0]

        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

        # Frequência da onda moduladora (gerador secundário)
        mod_freq = freq * ratio

        # Envelope de modulação dinâmico (o sino começa metálico e fecha em uma senoide suave)
        mod_env = np.exp(-mod_decay * t) * mod_index

        # Sinal modulador
        modulator = np.sin(2 * np.pi * mod_freq * t) * mod_env

        # Onda portadora principal (carrier) modulada em fase pela moduladora
        wave = np.sin(2 * np.pi * freq * t + modulator)

        # Envelope de amplitude geral (longa cauda clássica de sino)
        fade = np.exp(-3.5 * t)
        attack = np.minimum(1.0, t / 0.002)  # Ataque imediato de 2ms

        return wave * fade * attack * volume * velocity
