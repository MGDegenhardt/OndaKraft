import numpy as np
import pygame
import pygame.sndarray
from mixer import MixerChannel
from melody_synth import Note, MelodySynth

# Desenvolvimento do controle de tempo e sinal que torna o app polifonico
# MGDegenhardt, 2026 - OndaKraft (baseado no JRYBeats)

# Lista padrão de notas de C3 a C6 (invertida para que C6 fique no topo visual)
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def get_piano_notes() -> list[str]:
    notes = []
    # De C3 (MIDI 48) a C6 (MIDI 84)
    for midi in range(48, 85):
        octave = midi // 12 - 1
        name = NOTE_NAMES[midi % 12]
        notes.append(f"{name}{octave}")
    notes.reverse()  # Notas agudas no topo do grid
    return notes


class InstrumentTrack:
    def __init__(self, name: str, synth, num_steps: int = 32):
        """
        Representa uma trilha melódica customizada associada a um sintetizador matemático específico.
        Cada trilha gerencia sua própria grade de notas (Piano Roll) de 32 passos e seu próprio MixerChannel.
        """
        self.name = name.upper()
        self.synth = synth  # Instância da classe que estende BaseSynthesizer
        self.piano_notes = get_piano_notes()
        self.num_steps = num_steps

        # Inicializa a matriz do piano roll (linhas de notas x colunas de passos de 32 compassos)
        self.pattern: list[list[Note | None]] = [
            [None for _ in range(num_steps)] for _ in range(len(self.piano_notes))
        ]

        # Canal de volume e pan individual no mixer para esta pista
        self.mixer_channel = MixerChannel(name=name, volume=0.7)

    def set_note_at(self, note_index: int, step: int, note: Note):
        """Define uma nota musical em uma posição específica do grid."""
        if 0 <= note_index < len(self.piano_notes) and 0 <= step < self.num_steps:
            self.pattern[note_index][step] = note

    def clear_note_at(self, note_index: int, step: int):
        """Remove a nota de uma posição específica do grid."""
        if 0 <= note_index < len(self.piano_notes) and 0 <= step < self.num_steps:
            self.pattern[note_index][step] = None


class Sequencer:
    def __init__(self, num_steps: int = 32):
        """
        Coordenador de reprodução temporal da DAW OndaKraft.
        Gerencia o passo atual e ativa a execução de bateria, sintetizadores polifônicos e clipes de áudio.
        """
        self.num_steps = num_steps
        self.current_step = 0

    def play_step(self, step: int, bpm: float, drum_tracks: list, instrument_tracks: list[InstrumentTrack],
                  audio_tracks: list, drum_sounds_map: dict, melody_synth: MelodySynth, all_channels: list):
        """
        Executa os sons ativos para o passo atual (step 0 a 31).
        A bateria lê seu padrão em loop de 16 passos usando (step % 16).
        Cada instrumento melódico gera som usando seu respectivo sintetizador matemático em tempo real.
        """
        # 1. Toca Trilhas de Bateria (Drum Tracks) em Loop de 16 Passos
        drum_step = step % 16
        for track in drum_tracks:
            if track.get('pattern', [])[drum_step]:
                mixer_channel = track.get('mixer_channel')
                if mixer_channel and mixer_channel.is_audible(all_channels):
                    sound_key = track.get('name')
                    wave_key = f"{sound_key}_WAVE"
                    raw_wave = drum_sounds_map.get(wave_key)

                    if raw_wave is not None:
                        # Processa a onda crua do drum com efeitos em tempo real (Distorção, Reverb, etc.)
                        processed_wave = mixer_channel.process_audio(raw_wave)
                        clipped_wave = np.clip(processed_wave, -1.0, 1.0)
                        audio_int16 = (clipped_wave * 32767).astype(np.int16)
                        stereo_wave = np.column_stack((audio_int16, audio_int16))
                        stereo_wave = np.ascontiguousarray(stereo_wave)
                        sound = pygame.sndarray.make_sound(stereo_wave)
                    else:
                        sound = drum_sounds_map.get(sound_key)

                    if sound:
                        channel = sound.play()
                        if channel:
                            left, right = mixer_channel.pan_to_lr()
                            channel.set_volume(left, right)

        # 2. Toca as Trilhas de Instrumentos Melódicos de Forma Polifônica Independente
        for track in instrument_tracks:
            if not track.mixer_channel.is_audible(all_channels):
                continue

            for note_idx in range(len(track.piano_notes)):
                note_obj = track.pattern[note_idx][step]
                if note_obj is not None:
                    # Calcula a frequência física e duração exata do som em segundos com base no BPM
                    freq = melody_synth.note_frequency(note_obj.pitch)
                    step_duration_sec = 60.0 / bpm / 4.0
                    duration = note_obj.duration_steps * step_duration_sec

                    # Chama o gerador matemático do sintetizador específico desta pista!
                    wave = track.synth.generate_wave(freq, duration, 44100, note_obj.velocity)

                    # Processa a onda resultante na mesa de efeitos individual deste canal do Mixer
                    processed_wave = track.mixer_channel.process_audio(wave)

                    clipped_wave = np.clip(processed_wave, -1.0, 1.0)
                    audio_int16 = (clipped_wave * 32767).astype(np.int16)
                    stereo_wave = np.column_stack((audio_int16, audio_int16))
                    stereo_wave = np.ascontiguousarray(stereo_wave)

                    sound = pygame.sndarray.make_sound(stereo_wave)
                    channel = sound.play()
                    if channel:
                        left, right = track.mixer_channel.pan_to_lr()
                        channel.set_volume(left, right)

        # 3. Toca Trilhas de Áudio Externo Importadas (Audio Tracks)
        for audio_track in audio_tracks:
            if audio_track.start_step == step:
                if audio_track.mixer_channel.is_audible(all_channels):
                    channel = audio_track.sound.play()
                    if channel:
                        left, right = audio_track.mixer_channel.pan_to_lr()
                        channel.set_volume(left, right)
