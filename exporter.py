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
        """
        Renderizador offline do OndaKraft.
        Processa matematicamente todas as pistas (bateria em loop, sintetizadores e trilhas de áudio),
        aplica os efeitos de canais individuais e exporta tudo para um arquivo WAV de estúdio.
        """
        self.sample_rate = sample_rate

    def export_project_to_wav(self, filepath: str, bpm: float, drum_tracks: list,
                              instrument_tracks: list[InstrumentTrack], audio_tracks: list,
                              drum_synth: DrumSynthesizer, melody_synth: MelodySynth):
        """
        Renderiza o projeto offline de forma assíncrona com 32 passos completos de composição,
        somando e tratando canais de forma estéreo através de matrizes NumPy.
        """
        num_steps = 32
        step_duration_sec = 60.0 / bpm / 4.0
        total_duration_sec = num_steps * step_duration_sec
        total_samples = int(self.sample_rate * total_duration_sec)

        # Buffer master de áudio em ponto flutuante estéreo (L e R)
        master_buffer = np.zeros((total_samples, 2), dtype=np.float32)

        # 1. Renderiza e soma as Trilhas de Bateria (Drum Tracks) em Loop de 16 Passos
        for track in drum_tracks:
            # Padrão original de 16 passos da bateria
            pattern = track.get('pattern', [False] * 16)
            mixer_channel = track.get('mixer_channel')
            name = track.get('name', 'KICK')

            # Escolhe o algoritmo de síntese matemática correspondente
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

            # Processa a onda através da cadeia de efeitos do canal (Distorção, Delay, etc.)
            if mixer_channel:
                drum_wave = mixer_channel.process_audio(drum_wave)
                left_gain, right_gain = mixer_channel.pan_to_lr()
            else:
                left_gain, right_gain = 0.85, 0.85

            for step in range(num_steps):
                # Uso de operador de módulo para a repetição da bateria de 16 passos ao longo de 32 passos
                drum_step = step % 16
                if pattern[drum_step]:
                    start_sample = int(step * step_duration_sec * self.sample_rate)
                    end_sample = min(start_sample + len(drum_wave), total_samples)
                    chunk_len = end_sample - start_sample

                    # Distribui com balanço de panorâmica e fader
                    master_buffer[start_sample:end_sample, 0] += drum_wave[:chunk_len] * left_gain
                    master_buffer[start_sample:end_sample, 1] += drum_wave[:chunk_len] * right_gain

        # 2. Renderiza e soma as Trilhas de Instrumentos Melódicos de Forma Polifônica (Multitrack)
        for track in instrument_tracks:
            mixer_channel = track.mixer_channel
            left_gain, right_gain = mixer_channel.pan_to_lr()

            for step in range(num_steps):
                for note_idx in range(len(track.piano_notes)):
                    note_obj = track.pattern[note_idx][step]
                    if note_obj is not None:
                        start_sample = int(step * step_duration_sec * self.sample_rate)

                        # Extrai a frequência e o comprimento físico em segundos
                        freq = melody_synth.note_frequency(note_obj.pitch)
                        duration = note_obj.duration_steps * step_duration_sec

                        # Gera a onda usando o sintetizador específico da trilha!
                        note_wave = track.synth.generate_wave(freq, duration, self.sample_rate, note_obj.velocity)

                        # Processa com fader e efeitos do canal
                        note_wave = mixer_channel.process_audio(note_wave)

                        end_sample = min(start_sample + len(note_wave), total_samples)
                        chunk_len = end_sample - start_sample

                        # Distribui nos canais Esquerdo e Direito do master
                        master_buffer[start_sample:end_sample, 0] += note_wave[:chunk_len] * left_gain
                        master_buffer[start_sample:end_sample, 1] += note_wave[:chunk_len] * right_gain

        # 3. Renderiza e soma as Trilhas de Áudio Externo (Audio Tracks)
        for audio_track in audio_tracks:
            mixer_channel = audio_track.mixer_channel
            left_gain, right_gain = mixer_channel.pan_to_lr()

            start_step = audio_track.start_step
            start_sample = int(start_step * step_duration_sec * self.sample_rate)

            if start_sample >= total_samples:
                continue

            try:
                # Extrai dados de áudio cru
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

        # 4. Limiter (Prevent Clipping) - Impede distorções desagradáveis de estouro de escala digital
        master_buffer = np.clip(master_buffer, -1.0, 1.0)

        # 5. Converte de float32 (-1.0 a 1.0) para Inteiro de 16-bits (-32768 a 32767)
        audio_int16 = (master_buffer * 32767).astype(np.int16)

        # 6. Grava fisicamente em disco utilizando o formatador nativo WAVE do Python
        with wave.open(filepath, 'wb') as wav_file:
            wav_file.setnchannels(2)  # Estéreo (2 canais)
            wav_file.setsampwidth(2)  # 16-bit (2 bytes por amostra)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

        print(f"Renderização offline realizada! Arquivo de 32 passos salvo em: {filepath}")
