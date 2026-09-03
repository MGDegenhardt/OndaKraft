import numpy as np
from base_synth import BaseSynthesizer

# Sintetizador de cordas
# MGDegenhardt, 2026 - OndaKraft

class StringSynth(BaseSynthesizer):
    def __init__(self):
        """
        StringSynth - Sintetizador de Modelagem Física Karplus-Strong.
        Simula o comportamento mecânico de uma corda dedilhada (violão, harpa, alaúde).
        """
        super().__init__("STRING")
        # Parâmetros customizáveis via janela de moldar timbre: [atual, min, max]
        self.parameters = {
            "Amortecimento (Damp)": [0.985, 0.85, 0.999],
            "Brilho do Ataque (Pluck)": [0.6, 0.1, 1.0],
            "Volume Global": [0.7, 0.1, 1.0]
        }

    def generate_wave(self, freq: float, duration: float, sample_rate: int = 44100,
                      velocity: float = 1.0) -> np.ndarray:
        damp = self.parameters["Amortecimento (Damp)"][0]
        pluck_noise = self.parameters["Brilho do Ataque (Pluck)"][0]
        volume = self.parameters["Volume Global"][0]

        # Período fundamental em amostras físicas
        N = int(sample_rate / freq)
        N = max(2, N)  # Prevenção contra estouro de frequência

        # Inicializa o buffer com ruído branco para modelar a batida inicial (pluck)
        # Mais brilho = mais ruído inicial agressivo
        ring_buf = np.random.uniform(-1.0, 1.0, N) * pluck_noise

        total_samples = int(sample_rate * duration)
        out = np.zeros(total_samples, dtype=np.float32)

        # Algoritmo circular Karplus-Strong altamente otimizado por ponteiros virtuais
        ptr = 0
        for i in range(total_samples):
            out[i] = ring_buf[ptr]
            next_ptr = (ptr + 1) % N
            # Filtro passa-baixas físico de média móvel com amortecimento
            ring_buf[ptr] = 0.5 * (ring_buf[ptr] + ring_buf[next_ptr]) * damp
            ptr = next_ptr

        # Envelope suave de fade-in e fade-out complementar para eliminar cliques na cauda
        attack = np.minimum(1.0, np.linspace(0, duration, total_samples, endpoint=False) / 0.002)  # Ataque imediato
        fade = np.linspace(1.0, 0.0, total_samples)  # Fade out linear suave para fechar o bloco

        return out * attack * fade * volume * velocity
