import numpy as np
import pygame
import pygame.sndarray
from mixer import MixerChannel
from melody_synth import Note, MelodySynth

    # Desenvolvimento do controle de tempo e sinal que torna o app polifonico
    # MGDegenhardt, 2026 - OndaKraft (baseado no JRYBeats)

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def get_piano_notes() -> list[str]:
    notes = []
    for midi in range(48, 85):
        octave = midi // 12 - 1
        name = NOTE_NAMES[midi % 12]
        notes.append(f"{name}{octave}")
    notes.reverse()
    return notes


class InstrumentTrack:
    def __init__(self, name: str, instrument_type: str, num_steps: int = 16):
        self.name = name
        self.instrument_type = instrument_type
        self.piano_notes = get_piano_notes()
        self.num_steps = num_steps
        self.pattern = [[None for _ in range(num_steps)] for _ in range(len(self.piano_notes))]
        self.mixer_channel = MixerChannel(name=name, volume=0.7)

    def set_note_at(self, note_index: int, step: int, note: Note):
        if 0 <= note_index < len(self.piano_notes) and 0 <= step < self.num_steps:
            self.pattern[note_index][step] = note

    def clear_note_at(self, note_index: int, step: int):
        if 0 <= note_index < len(self.piano_notes) and 0 <= step < self.num_steps:
            self.pattern[note_index][step] = None


class Sequencer:
    def __init__(self, num_steps: int = 16):
        self.num_steps = num_steps
        self.current_step = 0

    def play_step(self, step: int, bpm: float, drum_tracks: list, instrument_tracks: list[InstrumentTrack],
                  audio_tracks: list, drum_sounds_map: dict, melody_synth: MelodySynth, all_channels: list):
        """Dispara áudios matemáticos e físicos por passo com faders aplicados [12]."""
        # Baterias
        for track in drum_tracks:
            if track.get('pattern', [])[step]:
                mixer_channel = track.get('mixer_channel')
                if mixer_channel and mixer_channel.is_audible(all_channels):
                    sound = drum_sounds_map.get(track.get('name'))
                    if sound:
                        channel = sound.play()
                        if channel:
                            left, right = mixer_channel.pan_to_lr()
                            channel.set_volume(left, right)

        # Instrumentos Melódicos
        for track in instrument_tracks:
            if not track.mixer_channel.is_audible(all_channels):
                continue

            for note_idx in range(len(track.piano_notes)):
                note_obj = track.pattern[note_idx][step]
                if note_obj is not None:
                    wave = melody_synth.create_dynamic_wave(note_obj, bpm)
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

        # Trilha de Áudio timeline
        for audio_track in audio_tracks:
            if audio_track.start_step == step:
                if audio_track.mixer_channel.is_audible(all_channels):
                    channel = audio_track.sound.play()
                    if channel:
                        left, right = audio_track.mixer_channel.pan_to_lr()
                        channel.set_volume(left, right)