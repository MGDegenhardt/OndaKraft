import numpy as np

# Desenvolvimento da secao a partid de onde os instrumentos sao carregados
# os instrumentos sao carregados somente a partir da pasta ./synths
# classe abastrata
# MGDegenhardt, 2026 - OndaKraft (baseado no JRYBeats)

class BaseSynthesizer:
    def __init__(self, name: str):
        """
        Classe base para todos os sintetizadores matemáticos do OndaKraft.
        Qualquer novo synth criado deve herdar desta classe e implementar generate_wave.
        """
        self.name = name.upper()
        # parameters format: { "DisplayName": [current_value, min_value, max_value] }
        self.parameters = {
            "Volume Global": [0.65, 0.0, 1.0],
            "Ataque (Attack)": [0.01, 0.001, 0.3]
        }

    def generate_wave(self, freq: float, duration: float, sample_rate: int = 44100,
                      velocity: float = 1.0) -> np.ndarray:
        """
        Gera o array NumPy contendo a forma de onda acústica para a frequência e tempo informados.
        Esta implementação padrão gera uma senóide pura básica com decaimento exponencial suave.
        """
        volume = self.parameters["Volume Global"][0]
        attack_time = self.parameters["Ataque (Attack)"][0]

        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        wave = np.sin(2 * np.pi * freq * t)
        fade = np.exp(-5.0 * t)
        attack = np.minimum(1.0, t / max(0.001, attack_time))  # 10ms de fade-in padrão
        return wave * fade * attack * volume * velocity