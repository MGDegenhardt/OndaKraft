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

    def generate_wave(self, freq: float, duration: float, sample_rate: int = 44100, velocity: float = 1.0) -> np.ndarray:
        """
        Gera o array NumPy contendo a forma de onda acústica para a frequência e tempo informados.
        Esta implementação padrão gera uma senóide pura básica com decaimento exponencial suave.
        """
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        wave = np.sin(2 * np.pi * freq * t)
        fade = np.exp(-5.0 * t)
        attack = np.minimum(1.0, t / 0.01) # 10ms de fade-in para evitar cliques
        return wave * fade * attack * 0.65 * velocity