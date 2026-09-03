import numpy as np
from base_synth import BaseSynthesizer

# Sintetizador de ondas ligeiraamente desalinhados para gerar pads basicos
# MGDegenhardt, 2026 - OndaKraft

class PadSynth(BaseSynthesizer):
    def __init__(self):
        """
        PadSynth - Sintetizador de Atmosferas e Ambient Pads.
        Gera sons etéreos, lentos e espaciais. Combina três osciladores senoidais desafinados com
        um tempo de ataque extremamente longo (fade-in gradual) e longa liberação (release).
        """
        super().__init__("PAD")
        # Parâmetros customizáveis via janela de moldar timbre: [atual, min, max]
        self.parameters = {
            "Tempo de Ataque (Attack Sec)": [1.5, 0.1, 2.5],
            "Desafinacao Chorus (Detune)": [2.5, 0.2, 5.0],
            "Peso do Subgrave": [0.35, 0.0, 1.0],
            "Volume Global": [0.5, 0.1, 1.0]
        }

    def generate_wave(self, freq: float, duration: float, sample_rate: int = 44100,
                      velocity: float = 1.0) -> np.ndarray:
        attack_sec = self.parameters["Tempo de Ataque (Attack Sec)"][0]
        detune = self.parameters["Desafinacao Chorus (Detune)"][0]
        sub_gain = self.parameters["Peso do Subgrave"][0]
        volume = self.parameters["Volume Global"][0]

        total_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, total_samples, endpoint=False)

        # Oscilador 1: Fundamental
        wave = np.sin(2 * np.pi * freq * t) * 0.45

        # Osciladores 2 e 3: Desafinados (Gera o efeito "chorus" físico e espacial)
        wave += np.sin(2 * np.pi * (freq - detune) * t) * 0.22
        wave += np.sin(2 * np.pi * (freq + detune) * t) * 0.22

        # Oscilador 4: Sub-oitava grave para peso de fundo (pad encorpado)
        wave += np.sin(2 * np.pi * (freq * 0.5) * t) * sub_gain * 0.35

        # Envelopes de Amplitude Ambientais
        fade = np.exp(-1.2 * t)  # Decaimento bem longo e lento

        # Tempo de ataque ajustável (suave surgimento do som)
        attack = np.minimum(1.0, t / max(0.005, attack_sec))

        # Fade-out linear complementar no final do bloco para transição macia entre passos
        fade_out = np.linspace(1.0, 0.0, total_samples)

        return wave * fade * attack * fade_out * volume * velocity