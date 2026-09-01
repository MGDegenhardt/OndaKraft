import numpy as np
    # Desenvolvimento de sintetizador de 'melody_synth' baseado em equações matemáticas e processamento de sinal
    # MGDegenhardt, 2025 - OndaKraft (baseado no JRYBeats)

class Note:
    def __init__(self, pitch: str, instrument: str, duration_steps: int = 1, velocity: float = 1.0):
        """
        Representa uma nota musical no Piano Roll do OndaKraft com propriedades expressivas.

        :param pitch: Nome da nota e oitava (ex: 'C4', 'F#3')
        :param instrument: O sintetizador associado (ex: 'SOFT', 'PLUCK', 'BASS', 'GUITAR', 'BRIGHT_SYNTH')
        :param duration_steps: Quantos passos (quadrados) de sequenciador a nota dura (padrão: 1)
        :param velocity: A força/volume individual da nota (0.0 a 1.0)
        """
        self.pitch = pitch
        self.instrument = instrument
        self.duration_steps = max(1, duration_steps)
        self.velocity = max(0.0, min(1.0, velocity))


class MelodySynth:
    def __init__(self, sample_rate: int = 44100):
        """
        Sintetizador melódico matemático do OndaKraft.
        Converte notas musicais em frequências e gera formas de onda ricas em harmônicos
        com durações dinâmicas calculadas com base no BPM da sessão.
        """
        self.sample_rate = sample_rate
        self.note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    def note_to_midi(self, note: str) -> int:
        """
        Converte uma string de nota (ex: 'C4') em seu valor numérico MIDI correspondente.
        """
        if '#' in note:
            note_name = note[:2]
            octave = int(note[2:])
        else:
            note_name = note
            octave = int(note[1:])
        return 12 * (octave + 1) + self.note_names.index(note_name)

    def note_frequency(self, note: str) -> float:
        """
        Calcula a frequência em Hertz (Hz) de uma nota a partir do seu valor MIDI.
        """
        midi = self.note_to_midi(note)
        return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))

    def create_dynamic_wave(self, note: Note, bpm: float) -> np.ndarray:
        """
        Gera dinamicamente o array de onda NumPy para uma determinada nota.
        A duração física em segundos é calculada em tempo real com base no BPM.
        """
        freq = self.note_frequency(note.pitch)

        # Calcula o tempo de um passo (step) em segundos com base no BPM
        step_duration_sec = 60.0 / bpm / 4.0
        duration = note.duration_steps * step_duration_sec

        count = int(self.sample_rate * duration)
        note_t = np.linspace(0, duration, count, endpoint=False)

        instrument = note.instrument

        # Ajuste de oitava para o contrabaixo
        if instrument == 'BASS':
            freq /= 2.0

        # Geração de harmônicos e envelopes baseados no JRYBeats original e novos instrumentos
        if instrument == 'SOFT':
            # Fundamental + 2º harmônico sutil
            note_wave = np.sin(2 * np.pi * freq * note_t) * 0.75
            note_wave += np.sin(2 * np.pi * freq * 2.0 * note_t) * 0.15
            fade = np.exp(-5.0 * note_t)

        elif instrument == 'PLUCK':
            # Ataque imediato e decaimento ultra agressivo
            note_wave = np.sin(2 * np.pi * freq * note_t) * 0.65
            note_wave += np.sin(2 * np.pi * freq * 2.0 * note_t) * 0.25
            fade = np.exp(-14.0 * note_t)

        elif instrument == 'BASS':
            # Sub-grave encorpado com decaimento moderado
            note_wave = np.sin(2 * np.pi * freq * note_t) * 0.80
            note_wave += np.sin(2 * np.pi * freq * 2.0 * note_t) * 0.12
            fade = np.exp(-6.0 * note_t)

        elif instrument == 'KEYS':
            # Som rico de piano elétrico (combina 3 harmônicos)
            note_wave = np.sin(2 * np.pi * freq * note_t) * 0.55
            note_wave += np.sin(2 * np.pi * freq * 2.0 * note_t) * 0.22
            note_wave += np.sin(2 * np.pi * freq * 3.0 * note_t) * 0.10
            fade = np.exp(-4.0 * note_t)

        elif instrument == 'GUITAR':
            # Novo instrumento: Guitarra acústica com brilho metálico (harmônicos de corda de nylon)
            note_wave = np.sin(2 * np.pi * freq * note_t) * 0.60
            note_wave += np.sin(2 * np.pi * freq * 2.0 * note_t) * 0.20
            note_wave += np.sin(2 * np.pi * freq * 3.0 * note_t) * 0.15
            fade = np.exp(-10.0 * note_t)

        elif instrument == 'BRIGHT_SYNTH':
            # Novo instrumento: Sintetizador eletrônico futurista com decaimento suave (sustain longo)
            note_wave = np.sin(2 * np.pi * freq * note_t) * 0.50
            note_wave += np.sin(2 * np.pi * freq * 2.0 * note_t) * 0.25
            note_wave += np.sin(2 * np.pi * freq * 3.0 * note_t) * 0.15
            note_wave += np.sin(2 * np.pi * freq * 4.0 * note_t) * 0.10
            fade = np.exp(-3.0 * note_t)

        else:
            # Fallback seguro
            note_wave = np.sin(2 * np.pi * freq * note_t)
            fade = np.exp(-5.0 * note_t)

        # Suavização do ataque (10ms) para impedir cliques de fase desagradáveis no início do som
        attack = np.minimum(1.0, note_t / 0.01)

        # Aplica o envelope e escala de ganho padrão (0.65) multiplicada pelo velocity da nota
        final_wave = note_wave * fade * attack * 0.65 * note.velocity
        return final_wave