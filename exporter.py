import wave
import numpy as np
import pygame
import pygame.sndarray
from mixer import MixerChannel
from drum_synth import DrumSynthesizer
from melody_synth import MelodySynth, Note
from sequencer import InstrumentTrack


# Desenvolvimento do setor responsavel pela exportacao da musica em wav, ogg ou mp3
# MGDegenhardt, 2026 - OndaKraft (baseado no JRYBeats)

class AudioExporter:
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

    def export_project_to_wav(self, filepath: str, bpm: float, drum_tracks: list,
                              instrument_tracks: list[InstrumentTrack], audio_tracks: list,
                              drum_synth: DrumSynthesizer, melody_synth: MelodySynth):
        num_steps = 16
        step_duration_sec = 60.0 / bpm / 4.0
        total_duration_sec = num_steps * step_duration_sec
        total_samples = int(self.sample_rate * total_duration_sec)

        master_buffer = np.zeros((total_samples, 2), dtype=np.float32)

        # Baterias
        for track in drum_tracks:
            pattern = track.get('pattern', [False] * num_steps)
            mixer_channel = track.get('mixer_channel')
            name = track.get('name', 'KICK')

            if name == 'KICK':
                drum_wave = drum_synth.generate_kick()
            elif name == 'SNARE':
                drum_wave = drum_synth.generate_snare()
            elif name == 'HI-HAT':
                drum_wave = drum_synth.generate_hihat()
            elif name == 'CLAP':
                drum_wave = drum_synth.generate_clap()
            else:
                drum_wave = drum_synth.generate_perc()

            if mixer_channel:
                drum_wave = mixer_channel.process_audio(drum_wave)
                left_gain, right_gain = mixer_channel.pan_to_lr()
            else:
                left_gain, right_gain = 0.85, 0.85

            for step in range(num_steps):
                if pattern[step]:
                    start_sample = int(step * step_duration_sec * self.sample_rate)
                    end_sample = min(start_sample + len(drum_wave), total_samples)
                    chunk_len = end_sample - start_sample
                    master_buffer[start_sample:end_sample, 0] += drum_wave[:chunk_len] * left_gain
                    master_buffer[start_sample:end_sample, 1] += drum_wave[:chunk_len] * right_gain

        # Melodias
        for track in instrument_tracks:
            mixer_channel = track.mixer_channel
            left_gain, right_gain = mixer_channel.pan_to_lr()

            for step in range(num_steps):
                for note_idx in range(len(track.piano_notes)):
                    note_obj = track.pattern[note_idx][step]
                    if note_obj is not None:
                        start_sample = int(step * step_duration_sec * self.sample_rate)
                        note_wave = melody_synth.create_dynamic_wave(note_obj, bpm)
                        note_wave = mixer_channel.process_audio(note_wave)

                        end_sample = min(start_sample + len(note_wave), total_samples)
                        chunk_len = end_sample - start_sample
                        master_buffer[start_sample:end_sample, 0] += note_wave[:chunk_len] * left_gain
                        master_buffer[start_sample:end_sample, 1] += note_wave[:chunk_len] * right_gain

        # Timeline de áudio externo
        for audio_track in audio_tracks:
            mixer_channel = audio_track.mixer_channel
            left_gain, right_gain = mixer_channel.pan_to_lr()
            start_step = audio_track.start_step
            start_sample = int(start_step * step_duration_sec * self.sample_rate)

            if start_sample >= total_samples:
                continue

            try:
                raw_array = pygame.sndarray.array(audio_track.sound)
                raw_array = raw_array.astype(np.float32)

                if len(raw_array.shape) == 2:
                    peak = np.max(np.abs(raw_array))
                    if peak > 0:
                        raw_array /= peak
                else:
                    peak = np.max(np.abs(raw_array))
                    if peak > 0:
                        raw_array /= peak
                    raw_array = np.column_stack((raw_array, raw_array))

                left_channel = mixer_channel.process_audio(raw_array[:, 0])
                right_channel = mixer_channel.process_audio(raw_array[:, 1])

                end_sample = min(start_sample + len(left_channel), total_samples)
                chunk_len = end_sample - start_sample
                master_buffer[start_sample:end_sample, 0] += left_channel[:chunk_len] * left_gain
                master_buffer[start_sample:end_sample, 1] += right_channel[:chunk_len] * right_gain

            except Exception as e:
                print(f"Erro ao exportar trilha de áudio {audio_track.name}: {e}")

        # Limiter de segurança contra clipping estourado
        master_buffer = np.clip(master_buffer, -1.0, 1.0)
        audio_int16 = (master_buffer * 32767).astype(np.int16)

        with wave.open(filepath, 'wb') as wav_file:
            wav_file.setnchannels(2)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

        print(f"Renderização concluída: {filepath}")
