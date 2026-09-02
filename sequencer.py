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
    def __init__(self, name: str, instrument_type: str, num_steps: int = 16):
        """
        Representa uma trilha melódica customizada (sintetizador ou instrumento de corda).
        Cada trilha gerencia sua própria grade de notas (Piano Roll) e seu MixerChannel.
        """
        self.name = name
        self.instrument_type = instrument_type  # Ex: 'SOFT', 'PLUCK', 'BASS', 'KEYS', 'GUITAR', 'BRIGHT_SYNTH'
        self.piano_notes = get_piano_notes()
        self.num_steps = num_steps

        # Inicializa a matriz do piano roll (linhas de notas x colunas de passos)
        self.pattern: list[list[Note | None]] = [
            [None for _ in range(num_steps)] for _ in range(len(self.piano_notes))
        ]

        # Canal individual do mixer para esta trilha específica
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
    def __init__(self, num_steps: int = 16):
        """
        Coordenador de reprodução temporal da DAW OndaKraft.
        Gerencia o passo atual e ativa a execução de bateria, sintetizadores e clipes de áudio.
        """
        self.num_steps = num_steps
        self.current_step = 0

    def play_step(self, step: int, bpm: float, drum_tracks: list, instrument_tracks: list[InstrumentTrack],
                  audio_tracks: list, drum_sounds_map: dict, melody_synth: MelodySynth, all_channels: list):
        """
        Executa os sons ativos para um determinado passo (step).
        Calcula as ondas em tempo real, aplica os efeitos de canal e envia para o Pygame Mixer.
        """
        # 1. Toca Trilhas de Bateria (Drum Tracks)
        for track in drum_tracks:
            if track.get('pattern', [])[step]:
                mixer_channel = track.get('mixer_channel')
                if mixer_channel and mixer_channel.is_audible(all_channels):
                    sound_key = track.get('name')
                    wave_key = f"{sound_key}_WAVE"
                    raw_wave = drum_sounds_map.get(wave_key)

                    if raw_wave is not None:
                        # Processa a onda do bumbo/caixa através da cadeia de efeitos inserida no canal em tempo real!
                        processed_wave = mixer_channel.process_audio(raw_wave)
                        clipped_wave = np.clip(processed_wave, -1.0, 1.0)
                        audio_int16 = (clipped_wave * 32767).astype(np.int16)
                        stereo_wave = np.column_stack((audio_int16, audio_int16))
                        stereo_wave = np.ascontiguousarray(stereo_wave)
                        sound = pygame.sndarray.make_sound(stereo_wave)
                    else:
                        sound = drum_sounds_map.get(sound_key)

                    if sound:
                        # Executa o áudio no Pygame
                        channel = sound.play()
                        if channel:
                            # Aplica o pan e volume calculados
                            left, right = mixer_channel.pan_to_lr()
                            channel.set_volume(left, right)

        # 2. Toca Trilhas de Instrumento Melódico (Instrument Tracks)
        for track in instrument_tracks:
            if not track.mixer_channel.is_audible(all_channels):
                continue

            for note_idx in range(len(track.piano_notes)):
                note_obj = track.pattern[note_idx][step]
                if note_obj is not None:
                    # Gera a forma de onda do sintetizador melódico com base na nota e no BPM atual
                    wave = melody_synth.create_dynamic_wave(note_obj, bpm)

                    # Processa a onda através da cadeia de efeitos inserida no canal
                    processed_wave = track.mixer_channel.process_audio(wave)

                    # Converte a onda processada pelo NumPy para o formato executável do Pygame Mixer
                    clipped_wave = np.clip(processed_wave, -1.0, 1.0)
                    audio_int16 = (clipped_wave * 32767).astype(np.int16)
                    stereo_wave = np.column_stack((audio_int16, audio_int16))
                    stereo_wave = np.ascontiguousarray(stereo_wave)

                    sound = pygame.sndarray.make_sound(stereo_wave)
                    channel = sound.play()
                    if channel:
                        # Define os ganhos estéreos L/R finais
                        left, right = track.mixer_channel.pan_to_lr()
                        channel.set_volume(left, right)

        # 3. Toca Trilhas de Áudio Externo Importadas (Audio Tracks)
        for audio_track in audio_tracks:
            # Se o áudio estiver configurado para começar exatamente neste passo
            if audio_track.start_step == step:
                if audio_track.mixer_channel.is_audible(all_channels):
                    channel = audio_track.sound.play()
                    if channel:
                        left, right = audio_track.mixer_channel.pan_to_lr()
                        channel.set_volume(left, right)
