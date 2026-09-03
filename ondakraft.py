import os
import sys
import time
import json
import wave
import tkinter as tk
from tkinter import filedialog
import numpy as np
import pygame
import pygame.sndarray

# Desenvolvimento do controlador principal do app
# MGDegenhardt, 2026 - OndaKraft (baseado no JRYBeats)

# Importando nossos componentes modulares da DAW OndaKraft
from drum_synth import DrumSynthesizer
from melody_synth import MelodySynth, Note
from audio_track import AudioTrack
from sequencer import Sequencer, InstrumentTrack, get_piano_notes
from mixer import MixerChannel
from plugin_loader import PluginLoader

# Garante que a pasta 'plugins', 'synths' e a pasta atual estejam no sys.path para importação direta de submódulos
import sys
import os

_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)
_plugins_dir = os.path.join(_current_dir, "plugins")
if os.path.exists(_plugins_dir) and _plugins_dir not in sys.path:
    sys.path.insert(0, _plugins_dir)
_synths_dir = os.path.join(_current_dir, "synths")
if os.path.exists(_synths_dir) and _synths_dir not in sys.path:
    sys.path.insert(0, _synths_dir)

from synth_loader import SynthLoader

try:
    from base_synth import BaseSynthesizer
except ImportError:
    class BaseSynthesizer:
        def __init__(self, name: str):
            self.name = name.upper()

        def generate_wave(self, freq, duration, sample_rate=44100, velocity=1.0):
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            wave = np.sin(2 * np.pi * freq * t)
            fade = np.exp(-5.0 * t)
            attack = np.minimum(1.0, t / 0.01)
            return wave * fade * attack * 0.65 * velocity

try:
    try:
        from synths.soft_synth import SoftSynth
    except ImportError:
        from soft_synth import SoftSynth
except ImportError:
    class SoftSynth(BaseSynthesizer):
        def __init__(self): super().__init__("SOFT")

try:
    try:
        from synths.pluck_synth import PluckSynth
    except ImportError:
        from pluck_synth import PluckSynth
except ImportError:
    class PluckSynth(BaseSynthesizer):
        def __init__(self): super().__init__("PLUCK")

try:
    try:
        from synths.bass_synth import BassSynth
    except ImportError:
        from bass_synth import BassSynth
except ImportError:
    class BassSynth(BaseSynthesizer):
        def __init__(self): super().__init__("BASS")

# Importando os plugins de forma segura com fallback de bypass
try:
    from plugins import DelayPlugin
except ImportError:
    class DelayPlugin:
        def __init__(self, **kwargs):
            self.name = "Delay"
            self.enabled = False

        def process(self, wave): return wave

try:
    try:
        from plugins.tremolo import TremoloPlugin
    except ImportError:
        from tremolo import TremoloPlugin
except ImportError:
    class TremoloPlugin:
        def __init__(self, **kwargs):
            self.name = "Tremolo"
            self.enabled = False

        def process(self, wave): return wave

try:
    try:
        from plugins.distortion import DistortionPlugin
    except ImportError:
        from distortion import DistortionPlugin
except ImportError:
    class DistortionPlugin:
        def __init__(self, **kwargs):
            self.name = "Distortion"
            self.enabled = False

        def process(self, wave): return wave

try:
    try:
        from plugins.reverb import ReverbPlugin
    except ImportError:
        from reverb import ReverbPlugin
except ImportError:
    class ReverbPlugin:
        def __init__(self, **kwargs):
            self.name = "Reverb"
            self.enabled = False

        def process(self, wave): return wave

try:
    try:
        from plugins.eq import EQPlugin
    except ImportError:
        from eq import EQPlugin
except ImportError:
    class EQPlugin:
        def __init__(self, **kwargs):
            self.name = "EQ"
            self.enabled = False

        def process(self, wave): return wave

try:
    try:
        from plugins.compressor import CompressorPlugin
    except ImportError:
        from compressor import CompressorPlugin
except ImportError:
    class CompressorPlugin:
        def __init__(self, **kwargs):
            self.name = "Compressor"
            self.enabled = False

        def process(self, wave): return wave

try:
    try:
        from plugins.chorus import ChorusPlugin
    except ImportError:
        from chorus import ChorusPlugin
except ImportError:
    class ChorusPlugin:
        def __init__(self, **kwargs):
            self.name = "Chorus"
            self.enabled = False

        def process(self, wave): return wave

from exporter import AudioExporter

# Tentativa de importação do SoundDevice para gravação segura do microfone
try:
    import sounddevice as sd

    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    print("Aviso: sounddevice não encontrado. A funcionalidade de gravação de microfone estará indisponível.")

# Inicialização padrão do Pygame e do Mixer de Áudio
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2)

# Constantes de Janela e Design
WIDTH = 1000
HEIGHT = 650
BACKGROUND = (245, 245, 242)
TEXT_COLOR = (45, 45, 45)
SECONDARY_TEXT = (120, 120, 120)
LINE_COLOR = (70, 70, 70)
LIGHT_LINE = (205, 205, 200)
BLUE = (35, 85, 170)
PLAYHEAD_BLUE = (75, 135, 220)
GREEN = (40, 150, 65)
GREEN_HOVER = (55, 175, 80)
RED = (210, 60, 60)
PURPLE = (110, 95, 210)
PURPLE_HOVER = (130, 115, 225)
ORANGE = (215, 130, 45)
BUTTON_BACKGROUND = (250, 250, 247)
STEP_BACKGROUND = (252, 252, 250)
STEP_HOVER = (225, 225, 220)
BLACK_KEY = (45, 45, 48)
WHITE_KEY = (245, 245, 242)

# Configuração de Fontes Typográficas
title_font = pygame.font.Font(None, 40)
section_font = pygame.font.Font(None, 27)
track_font = pygame.font.Font(None, 25)
small_font = pygame.font.Font(None, 21)
tiny_font = pygame.font.Font(None, 17)
step_font = pygame.font.Font(None, 18)


# Função utilitária para converter onda NumPy em pygame.mixer.Sound
def make_sound(wave):
    wave = np.clip(wave, -1.0, 1.0)
    audio = (wave * 32767).astype(np.int16)
    stereo = np.column_stack((audio, audio))
    stereo = np.ascontiguousarray(stereo)
    return pygame.sndarray.make_sound(stereo)


# Iconografia em Vetores do Pygame (Mantém o app leve e sem dependências de arquivos externos)
def make_icon_surface(size=(48, 48)):
    return pygame.Surface(size, pygame.SRCALPHA)


def create_kick_icon():
    surface = make_icon_surface()
    pygame.draw.circle(surface, TEXT_COLOR, (24, 24), 18, 3)
    pygame.draw.circle(surface, SECONDARY_TEXT, (24, 24), 5, 2)
    pygame.draw.line(surface, TEXT_COLOR, (12, 38), (8, 46), 3)
    pygame.draw.line(surface, TEXT_COLOR, (36, 38), (40, 46), 3)
    return surface


def create_snare_icon():
    surface = make_icon_surface()
    pygame.draw.ellipse(surface, TEXT_COLOR, (7, 10, 34, 11), 2)
    pygame.draw.rect(surface, TEXT_COLOR, (7, 15, 34, 20), 2)
    pygame.draw.ellipse(surface, TEXT_COLOR, (7, 29, 34, 11), 2)
    pygame.draw.line(surface, SECONDARY_TEXT, (10, 20), (38, 31), 2)
    pygame.draw.line(surface, SECONDARY_TEXT, (10, 31), (38, 20), 2)
    return surface


def create_hihat_icon():
    surface = make_icon_surface()
    pygame.draw.line(surface, TEXT_COLOR, (24, 12), (24, 42), 3)
    pygame.draw.line(surface, TEXT_COLOR, (10, 19), (38, 19), 3)
    pygame.draw.line(surface, SECONDARY_TEXT, (13, 23), (35, 23), 2)
    pygame.draw.line(surface, TEXT_COLOR, (17, 42), (31, 42), 3)
    return surface


def create_clap_icon():
    surface = make_icon_surface()
    pygame.draw.polygon(surface, TEXT_COLOR,
                        [(8, 28), (14, 15), (18, 17), (16, 27), (22, 13), (26, 15), (22, 30), (29, 18), (33, 21),
                         (27, 35), (17, 39)], 2)
    pygame.draw.polygon(surface, SECONDARY_TEXT,
                        [(40, 26), (35, 14), (31, 17), (33, 27), (27, 13), (24, 16), (29, 31), (22, 20), (19, 23),
                         (25, 37), (35, 39)], 2)
    return surface


def create_perc_icon():
    surface = make_icon_surface()
    pygame.draw.ellipse(surface, TEXT_COLOR, (9, 5, 24, 28), 3)
    pygame.draw.line(surface, TEXT_COLOR, (27, 29), (39, 44), 5)
    pygame.draw.circle(surface, SECONDARY_TEXT, (19, 16), 3)
    pygame.draw.circle(surface, SECONDARY_TEXT, (25, 22), 3)
    return surface


def create_microphone_icon():
    surface = pygame.Surface((24, 24), pygame.SRCALPHA)
    pygame.draw.rect(surface, TEXT_COLOR, (8, 2, 8, 13), border_radius=4)
    pygame.draw.arc(surface, TEXT_COLOR, (5, 7, 14, 11), 3.14159, 6.28318, 2)
    pygame.draw.line(surface, TEXT_COLOR, (12, 17), (12, 22), 2)
    pygame.draw.line(surface, TEXT_COLOR, (8, 22), (16, 22), 2)
    return surface


# Instanciando as Imagens Vetoriais
kick_image = create_kick_icon()
snare_image = create_snare_icon()
hihat_image = create_hihat_icon()
clap_image = create_clap_icon()
perc_image = create_perc_icon()
microphone_image = create_microphone_icon()
drum_images = [kick_image, snare_image, hihat_image, clap_image, perc_image]


def init_channel_fx(channel):
    """Inicializa os 8 slots de efeitos padrão para um canal do mixer."""
    channel.effects_chain.clear()

    p_delay = DelayPlugin()
    p_delay.enabled = False
    channel.add_plugin(p_delay)

    p_tremolo = TremoloPlugin()
    p_tremolo.enabled = False
    channel.add_plugin(p_tremolo)

    p_dist = DistortionPlugin()
    p_dist.enabled = False
    channel.add_plugin(p_dist)

    p_reverb = ReverbPlugin()
    p_reverb.enabled = False
    channel.add_plugin(p_reverb)

    p_eq = EQPlugin()
    p_eq.enabled = False
    channel.add_plugin(p_eq)

    p_comp = CompressorPlugin()
    p_comp.enabled = False
    channel.add_plugin(p_comp)

    p_chorus = ChorusPlugin()
    p_chorus.enabled = False
    channel.add_plugin(p_chorus)

    # Slot 8: customizado / dinâmico (inicialmente vazio)
    class CustomSlotPlugin:
        def __init__(self):
            self.name = ""
            self.enabled = False

        def process(self, wave):
            return wave

    p_custom = CustomSlotPlugin()
    channel.add_plugin(p_custom)


class OndaKraftApp:
    def __init__(self):
        """
        Classe Controladora Principal do OndaKraft DAW.
        Gerencia telas, eventos Pygame, inicialização de áudio, gravação e persistência.
        """
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('OndaKraft DAW')
        self.clock = pygame.time.Clock()

        # Parâmetros Globais do Sequenciador
        self.bpm = 120
        self.min_bpm = 60
        self.max_bpm = 200
        self.playing = False
        self.current_step = 0
        self.next_step_time = 0
        self.current_view = 'SEQUENCER'  # Abas: 'SEQUENCER', 'PIANO', 'AUDIO', 'MIXER'
        self.dragging_audio = None
        self.mixer_drag = None

        # Motores e Sintetizadores Matemáticos
        self.drum_synth = DrumSynthesizer()
        self.melody_synth = MelodySynth()
        self.sequencer = Sequencer(num_steps=32)
        self.exporter = AudioExporter()

        # Variáveis e Retângulos de Paginação do Piano Roll (32 passos)
        self.piano_page = 0
        self.piano_auto_follow = True
        self.piano_page1_rect = pygame.Rect(750, 585, 100, 30)
        self.piano_page2_rect = pygame.Rect(865, 585, 100, 30)
        self.piano_follow_rect = pygame.Rect(750, 545, 215, 26)

        self.plugin_loader = PluginLoader("plugins")
        self.discovered_plugins = self.plugin_loader.discover_and_load()

        # Carrega Sons de Bateria Físicos na Memória do Pygame
        # Carrega Sons de Bateria Físicos na Memória do Pygame e guarda ondas cruas para efeitos em tempo real
        kick_raw = self.drum_synth.generate_kick()
        snare_raw = self.drum_synth.generate_snare()
        hihat_raw = self.drum_synth.generate_hihat()
        clap_raw = self.drum_synth.generate_clap()
        perc_raw = self.drum_synth.generate_perc()

        self.drum_sounds_map = {
            'KICK': make_sound(kick_raw),
            'KICK_WAVE': kick_raw,
            'SNARE': make_sound(snare_raw),
            'SNARE_WAVE': snare_raw,
            'HI-HAT': make_sound(hihat_raw),
            'HI-HAT_WAVE': hihat_raw,
            'CLAP': make_sound(clap_raw),
            'CLAP_WAVE': clap_raw,
            'PERC': make_sound(perc_raw),
            'PERC_WAVE': perc_raw
        }

        # Inicializa Estruturas de Trilha (Model)
        # 1. Trilhas de Bateria (Lista de Dicionários contendo MixerChannels individuais com delay embutido)
        self.drum_tracks_names = ['KICK', 'SNARE', 'HI-HAT', 'CLAP', 'PERC']
        self.drum_tracks = []
        for name in self.drum_tracks_names:
            mixer_ch = MixerChannel(name=name, volume=0.85)
            init_channel_fx(mixer_ch)

            self.drum_tracks.append({
                'name': name,
                'pattern': [False] * 16,
                'mixer_channel': mixer_ch
            })

            # 2. Trilhas Melódicas (Instrument Tracks) - Multitrack Dinâmica baseada em /synths
        self.synth_loader = SynthLoader("synths")
        self.discovered_synths = self.synth_loader.discover_and_load()

        self.available_synths = []
        for s_class in self.discovered_synths:
            try:
                self.available_synths.append(s_class())
            except Exception as e:
                print(f"Erro ao instanciar synth {s_class.__name__}: {e}")

        # Fallbacks caso não tenha nenhum arquivo na pasta /synths
        if not self.available_synths:
            self.available_synths.append(SoftSynth())
            self.available_synths.append(PluckSynth())
            self.available_synths.append(BassSynth())

        self.instrument_tracks = []
        for synth in self.available_synths:
            track = InstrumentTrack(synth.name, synth, num_steps=32)
            init_channel_fx(track.mixer_channel)
            self.instrument_tracks.append(track)

        self.active_instrument_track_index = 0

        # 3. Trilhas de Áudio Importadas
        self.audio_tracks: list[AudioTrack] = []

        # Elementos de Interface Visual (Retângulos dos Botões do Cabeçalho)
        self.play_rect = pygame.Rect(30, 82, 70, 42)
        self.stop_rect = pygame.Rect(115, 82, 70, 42)
        self.bpm_minus_rect = pygame.Rect(215, 82, 35, 42)
        self.bpm_rect = pygame.Rect(250, 82, 70, 42)
        self.bpm_plus_rect = pygame.Rect(320, 82, 35, 42)

        # Abas de Navegação
        self.sequencer_tab_rect = pygame.Rect(35, 150, 120, 40)
        self.piano_tab_rect = pygame.Rect(185, 150, 130, 40)
        self.audio_tab_rect = pygame.Rect(335, 150, 180, 40)
        self.mixer_tab_rect = pygame.Rect(545, 150, 80, 40)

        # Ações de Projeto / Arquivos
        self.save_project_rect = pygame.Rect(805, 153, 72, 32)
        self.load_project_rect = pygame.Rect(885, 153, 72, 32)
        self.export_project_rect = pygame.Rect(725, 153, 72, 32)

        # Visualização de Áudio (Importação / Microfone)
        self.import_audio_rect = pygame.Rect(25, 215, 82, 36)
        self.record_audio_rect = pygame.Rect(115, 215, 88, 36)

        # Seleção de Microfone
        self.mic_prev_rect = pygame.Rect(455, 88, 30, 30)
        self.mic_device_rect = pygame.Rect(490, 88, 420, 30)
        self.mic_next_rect = pygame.Rect(915, 88, 30, 30)

        # Estado e Variáveis do Microfone
        self.recording_microphone = False
        self.microphone_chunks = []
        self.microphone_stream = None
        self.microphone_record_samplerate = 44100
        self.selected_microphone_position = 0
        self.microphone_devices = []

        if SOUNDDEVICE_AVAILABLE:
            self.discover_microphones()

        # Posicionamento Dinâmico do Piano Roll
        self.piano_grid_start_x = 130
        self.piano_step_width = 45
        self.piano_grid_top = 225
        self.piano_row_height = 28
        self.visible_piano_rows = 11
        self.piano_scroll = 11  # Começa no meio do teclado

        # Posicionamento Dinâmico do Sequenciador de Bateria
        self.sequencer_start_x = 300
        self.track_start_y = 235
        self.row_height = 68
        self.step_size = 28
        self.step_gap = 8

        # Cores de Instrumentos
        self.INSTRUMENT_COLORS = {
            'SOFT': (110, 95, 210), 'PLUCK': (45, 155, 95), 'BASS': (215, 130, 45),
            'KEYS': (45, 125, 190), 'GUITAR': (180, 85, 85), 'BRIGHT_SYNTH': (40, 160, 150)
        }
        self.INSTRUMENT_HOVER_COLORS = {
            'SOFT': (130, 115, 225), 'PLUCK': (65, 175, 115), 'BASS': (230, 150, 65),
            'KEYS': (65, 145, 210), 'GUITAR': (200, 105, 105), 'BRIGHT_SYNTH': (60, 180, 170)
        }

    def discover_microphones(self):
        """Mapeia os microfones disponíveis no sistema operacional."""
        try:
            self.microphone_devices = [
                (idx, dev['name']) for idx, dev in enumerate(sd.query_devices())
                if dev['max_input_channels'] > 0
            ]
            default_input = sd.default.device[0]
            for pos, (idx, name) in enumerate(self.microphone_devices):
                if idx == default_input:
                    self.selected_microphone_position = pos
                    break
        except Exception as err:
            print("Erro ao listar microfones:", err)

    def get_selected_microphone(self):
        if not self.microphone_devices:
            return (None, 'MICROFONE NÃO ENCONTRADO')
        return self.microphone_devices[self.selected_microphone_position]

    def microphone_callback(self, indata, frames, time_info, status):
        if status:
            print("Microfone status:", status)
        if self.recording_microphone:
            self.microphone_chunks.append(indata.copy())

    def start_microphone_recording(self):
        if not SOUNDDEVICE_AVAILABLE:
            print("Sounddevice indisponível. Impossível gravar.")
            return

        self.microphone_chunks = []
        device_index, device_name = self.get_selected_microphone()
        if device_index is None:
            print("Nenhum dispositivo de entrada encontrado.")
            return

        try:
            device_info = sd.query_devices(device_index)
            record_samplerate = int(device_info['default_samplerate'])
            record_channels = min(1, device_info['max_input_channels'])

            if record_channels < 1:
                print("O dispositivo escolhido não possui canais de entrada:", device_name)
                return

            self.microphone_record_samplerate = record_samplerate
            self.microphone_stream = sd.InputStream(
                device=device_index,
                samplerate=record_samplerate,
                channels=record_channels,
                dtype='float32',
                callback=self.microphone_callback
            )
            self.microphone_stream.start()
            self.recording_microphone = True
            print(f"Gravando microfone: {device_name} @ {record_samplerate}Hz")
        except Exception as error:
            self.microphone_stream = None
            self.recording_microphone = False
            print(f"Erro ao iniciar gravação no microfone {device_name}: {error}")

    def stop_microphone_recording(self):
        self.recording_microphone = False
        if self.microphone_stream is not None:
            self.microphone_stream.stop()
            self.microphone_stream.close()
            self.microphone_stream = None

        if len(self.microphone_chunks) == 0:
            print("Gravação vazia.")
            return

        recording = np.concatenate(self.microphone_chunks, axis=0)
        recording = np.clip(recording, -1.0, 1.0)
        recording_int16 = (recording * 32767).astype(np.int16)

        filename = time.strftime('OndaKraft_recording_%Y%m%d_%H%M%S.wav')
        try:
            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.microphone_record_samplerate)
                wav_file.writeframes(recording_int16.tobytes())

            print(f"Gravação de áudio salva em: {filename}")

            # Importa o áudio gravado diretamente para a timeline através do Factory Method
            self.import_audio_track(filename)
        except Exception as err:
            print("Falha ao salvar arquivo gravado:", err)

    def import_audio_track(self, path: str):
        try:
            new_track = AudioTrack.from_file(path)
            init_channel_fx(new_track.mixer_channel)
            self.audio_tracks.append(new_track)
            print(f"Trilha importada com sucesso: {new_track.name}")
        except Exception as err:
            print(f"Erro ao importar {path}: {err}")

    def choose_and_import_file(self):
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askopenfilename(
            title='Importar Áudio para OndaKraft',
            filetypes=[('Arquivos de Áudio', '*.wav *.mp3 *.ogg'), ('WAV', '*.wav'), ('MP3', '*.mp3'), ('OGG', '*.ogg'),
                       ('Todos', '*.*')]
        )
        root.destroy()
        if path:
            self.import_audio_track(path)

    def get_all_channels(self) -> list[MixerChannel]:
        """Agrupa todos os canais do mixer em uso para processar Mute e Solo."""
        channels = []
        for track in self.drum_tracks:
            channels.append(track['mixer_channel'])
        for track in self.instrument_tracks:
            channels.append(track.mixer_channel)
        for track in self.audio_tracks:
            channels.append(track.mixer_channel)
        return channels

    def save_project_to_json(self):
        if self.recording_microphone:
            print("Pare a gravação antes de salvar o projeto.")
            return

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.asksaveasfilename(
            title='Salvar Projeto OndaKraft',
            defaultextension='.jry',
            filetypes=[('Projeto OndaKraft', '*.jry'), ('JSON', '*.json')]
        )
        root.destroy()
        if not path:
            return

        # Serializa o estado de todas as Trilhas Melódicas do projeto
        instrument_tracks_serialized = []
        for track in self.instrument_tracks:
            pattern_serialized = []
            for note_idx in range(len(track.piano_notes)):
                row = []
                for step in range(32):
                    note_obj = track.pattern[note_idx][step]
                    if note_obj is not None:
                        row.append({
                            'pitch': note_obj.pitch,
                            'instrument': note_obj.instrument,
                            'duration_steps': note_obj.duration_steps,
                            'velocity': note_obj.velocity
                        })
                    else:
                        row.append(None)
                pattern_serialized.append(row)

            instrument_tracks_serialized.append({
                'name': track.name,
                'synth_name': track.synth.name,
                'pattern': pattern_serialized,
                'mixer': {
                    'volume': track.mixer_channel.volume,
                    'muted': track.mixer_channel.muted,
                    'solo': track.mixer_channel.solo,
                    'pan': track.mixer_channel.pan,
                    'effects_chain': [p.enabled for p in track.mixer_channel.effects_chain]
                }
            })

        project_state = {
            'version': 3,
            'bpm': self.bpm,
            'current_view': self.current_view,
            'melody_instrument': self.melody_instrument,
            'piano_scroll': self.piano_scroll,
            # Bateria
            'drum_patterns': [t['pattern'] for t in self.drum_tracks],
            'drum_mixer': [{
                'volume': t['mixer_channel'].volume,
                'muted': t['mixer_channel'].muted,
                'solo': t['mixer_channel'].solo,
                'pan': t['mixer_channel'].pan,
                'delay_enabled': t['mixer_channel'].effects_chain[0].enabled,
                'effects_chain': [p.enabled for p in t['mixer_channel'].effects_chain],
                'effects_names': [p.name for p in t['mixer_channel'].effects_chain]
            } for t in self.drum_tracks],
            # Melodia
            'instrument_tracks': instrument_tracks_serialized,
            # Trilhas de Áudio Externas
            'audio_tracks': [{
                'name': t.name,
                'path': t.path,
                'start_step': t.start_step,
                'volume': t.mixer_channel.volume,
                'muted': t.mixer_channel.muted,
                'solo': t.mixer_channel.solo,
                'pan': t.mixer_channel.pan
            } for t in self.audio_tracks]
        }

        try:
            with open(path, 'w', encoding='utf-8') as pf:
                json.dump(project_state, pf, indent=2)
            print("Projeto OndaKraft salvo:", path)
        except Exception as err:
            print("Erro ao salvar projeto:", err)

    def load_project_from_json(self):
        if self.recording_microphone:
            print("Pare a gravação antes de carregar um projeto.")
            return

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askopenfilename(
            title='Carregar Projeto OndaKraft',
            filetypes=[('Projeto OndaKraft', '*.jry'), ('JSON', '*.json'), ('Todos os arquivos', '*.*')]
        )
        root.destroy()
        if not path:
            return

        try:
            with open(path, 'r', encoding='utf-8') as pf:
                state = json.load(pf)

            pygame.mixer.stop()
            self.playing = False
            self.current_step = 0

            self.bpm = max(self.min_bpm, min(self.max_bpm, int(state.get('bpm', self.bpm))))
            self.current_view = state.get('current_view', 'SEQUENCER')
            self.melody_instrument = state.get('melody_instrument', 'SOFT')
            self.piano_scroll = state.get('piano_scroll', self.piano_scroll)

            # Carrega Bateria
            loaded_drum_patterns = state.get('drum_patterns', [])
            loaded_drum_mixer = state.get('drum_mixer', [])
            for i, track in enumerate(self.drum_tracks):
                if i < len(loaded_drum_patterns):
                    track['pattern'] = loaded_drum_patterns[i]
                if i < len(loaded_drum_mixer):
                    mix = loaded_drum_mixer[i]
                    track['mixer_channel'].volume = mix.get('volume', 0.85)
                    track['mixer_channel'].muted = mix.get('muted', False)
                    track['mixer_channel'].solo = mix.get('solo', False)
                    track['mixer_channel'].pan = mix.get('pan', 0.0)
                    if 'effects_chain' in mix:
                        for idx, val in enumerate(mix['effects_chain']):
                            if idx < len(track['mixer_channel'].effects_chain):
                                track['mixer_channel'].effects_chain[idx].enabled = val
                    elif 'delay_enabled' in mix and len(track['mixer_channel'].effects_chain) > 0:
                        track['mixer_channel'].effects_chain[0].enabled = mix['delay_enabled']

            # Carrega Melodia (Instrument Track)
            self.melody_track = InstrumentTrack("Melodia", self.melody_instrument, num_steps=32)
            melody_delay = DelayPlugin(delay_time=0.33, feedback=0.35, mix=0.25)
            self.melody_track.mixer_channel.add_plugin(melody_delay)
            self.instrument_tracks = [self.melody_track]

            loaded_melody_mixer = state.get('melody_mixer', {})
            self.melody_track.mixer_channel.volume = loaded_melody_mixer.get('volume', 0.7)
            self.melody_track.mixer_channel.muted = loaded_melody_mixer.get('muted', False)
            self.melody_track.mixer_channel.solo = loaded_melody_mixer.get('solo', False)
            self.melody_track.mixer_channel.pan = loaded_melody_mixer.get('pan', 0.0)
            if 'effects_chain' in loaded_melody_mixer:
                for idx, val in enumerate(loaded_melody_mixer['effects_chain']):
                    if idx < len(self.melody_track.mixer_channel.effects_chain):
                        self.melody_track.mixer_channel.effects_chain[idx].enabled = val
            elif 'delay_enabled' in loaded_melody_mixer:
                self.melody_track.mixer_channel.effects_chain[0].enabled = loaded_melody_mixer['delay_enabled']

            loaded_melody_pattern = state.get('melody_pattern', [])
            piano_notes = get_piano_notes()
            for note_idx in range(len(piano_notes)):
                if note_idx >= len(loaded_melody_pattern):
                    continue
                num_loaded_steps = len(loaded_melody_pattern[note_idx]) if loaded_melody_pattern else 0
                for step in range(min(32, num_loaded_steps)):
                    cell = loaded_melody_pattern[note_idx][step]
                    if cell is not None:
                        # Se for do formato antigo (JRYBeats salva strings de instrumento diretamente)
                        if isinstance(cell, str):
                            inst = cell if cell in self.instruments else self.melody_instrument
                            note_obj = Note(pitch=piano_notes[note_idx], instrument=inst)
                        else:  # Novo formato robusto de Note serializada
                            note_obj = Note(
                                pitch=cell.get('pitch', piano_notes[note_idx]),
                                instrument=cell.get('instrument', self.melody_instrument),
                                duration_steps=cell.get('duration_steps', 1),
                                velocity=cell.get('velocity', 1.0)
                            )
                        self.melody_track.set_note_at(note_idx, step, note_obj)

            # Carrega Trilhas de Áudio Externas
            self.audio_tracks.clear()
            missing_files = []
            for saved_at in state.get('audio_tracks', []):
                file_path = saved_at.get('path', '')
                if not os.path.exists(file_path):
                    missing_files.append(file_path)
                    continue

                try:
                    loaded_track = AudioTrack.from_file(file_path)
                    init_channel_fx(loaded_track.mixer_channel)
                    loaded_track.start_step = saved_at.get('start_step', 0)
                    loaded_track.mixer_channel.volume = saved_at.get('volume', 0.8)
                    loaded_track.mixer_channel.muted = saved_at.get('muted', False)
                    loaded_track.mixer_channel.solo = saved_at.get('solo', False)
                    loaded_track.mixer_channel.pan = saved_at.get('pan', 0.0)
                    self.audio_tracks.append(loaded_track)
                except Exception as e:
                    print(f"Não pôde importar trilha salva {file_path}: {e}")

            print("Projeto OndaKraft carregado com sucesso!")
            if missing_files:
                print("Aviso: Alguns arquivos de áudio externos não foram encontrados:")
                for mf in missing_files:
                    print(" -", mf)
        except Exception as err:
            print("Falha ao carregar projeto OndaKraft:", err)

    def export_wav(self):
        if self.recording_microphone:
            print("Pare a gravação antes de exportar.")
            return

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.asksaveasfilename(
            title='Exportar Música como WAV',
            defaultextension='.wav',
            filetypes=[('Áudio WAV sem perdas', '*.wav')]
        )
        root.destroy()
        if not path:
            return

        try:
            print("Renderizando projeto de forma offline...")
            self.exporter.export_project_to_wav(
                filepath=path,
                bpm=self.bpm,
                drum_tracks=self.drum_tracks,
                instrument_tracks=self.instrument_tracks,
                audio_tracks=self.audio_tracks,
                drum_synth=self.drum_synth,
                melody_synth=self.melody_synth
            )
            print("Exportação concluída com absoluto sucesso!")
        except Exception as err:
            print("Falha na exportação offline:", err)

    def play_sound_from_mixer(self, sound, mixer_channel: MixerChannel):
        """Toca áudio em tempo real aplicando Mute/Solo e Pan do mixer."""
        if not mixer_channel.is_audible(self.get_all_channels()):
            return
        channel = sound.play()
        if channel:
            left, right = mixer_channel.pan_to_lr()
            channel.set_volume(left, right)

    def handle_pygame_events(self) -> bool:
        """Loop de captação de eventos de teclado, mouse, drag & drop e timeline."""
        now = pygame.time.get_ticks()
        piano_notes = get_piano_notes()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.DROPFILE:
                # Drag and drop de arquivo físico para a DAW
                self.import_audio_track(event.file)
                self.current_view = 'AUDIO'

            elif event.type == pygame.MOUSEWHEEL:
                if self.current_view == 'PIANO':
                    self.piano_scroll -= event.y
                    self.piano_scroll = max(0, min(self.piano_scroll, len(piano_notes) - self.visible_piano_rows))

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if self.playing:
                        self.playing = False
                        pygame.mixer.stop()
                    else:
                        self.playing = True
                        self.current_step = 0
                        self.sequencer.play_step(
                            self.current_step, self.bpm, self.drum_tracks, self.instrument_tracks,
                            self.audio_tracks, self.drum_sounds_map, self.melody_synth, self.get_all_channels()
                        )
                        step_interval = 60000 / self.bpm / 4
                        self.next_step_time = now + step_interval
                elif event.key == pygame.K_LEFT:
                    self.bpm = max(self.min_bpm, self.bpm - 5)
                elif event.key == pygame.K_RIGHT:
                    self.bpm = min(self.max_bpm, self.bpm + 5)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_x, click_y = event.pos

                # Cliques em Botões do Cabeçalho
                if self.play_rect.collidepoint(click_x, click_y):
                    if not self.playing:
                        self.playing = True
                        self.current_step = 0
                        self.sequencer.play_step(
                            self.current_step, self.bpm, self.drum_tracks, self.instrument_tracks,
                            self.audio_tracks, self.drum_sounds_map, self.melody_synth, self.get_all_channels()
                        )
                        step_interval = 60000 / self.bpm / 4
                        self.next_step_time = now + step_interval
                elif self.stop_rect.collidepoint(click_x, click_y):
                    self.playing = False
                    self.current_step = 0
                    pygame.mixer.stop()
                elif self.bpm_minus_rect.collidepoint(click_x, click_y):
                    self.bpm = max(self.min_bpm, self.bpm - 5)
                elif self.bpm_plus_rect.collidepoint(click_x, click_y):
                    self.bpm = min(self.max_bpm, self.bpm + 5)

                # Cliques nas Abas de Navegação
                elif self.sequencer_tab_rect.collidepoint(click_x, click_y):
                    self.current_view = 'SEQUENCER'
                elif self.piano_tab_rect.collidepoint(click_x, click_y):
                    self.current_view = 'PIANO'
                elif self.audio_tab_rect.collidepoint(click_x, click_y):
                    self.current_view = 'AUDIO'
                elif self.mixer_tab_rect.collidepoint(click_x, click_y):
                    self.current_view = 'MIXER'

                # Ações de Salvamento, Carregamento e Exportação
                elif self.save_project_rect.collidepoint(click_x, click_y):
                    self.save_project_to_json()
                elif self.load_project_rect.collidepoint(click_x, click_y):
                    self.load_project_from_json()
                elif self.export_project_rect.collidepoint(click_x, click_y):
                    self.export_wav()

                # Eventos de Áudio Externo
                elif self.current_view == 'AUDIO' and self.mic_prev_rect.collidepoint(click_x, click_y):
                    if self.microphone_devices and (not self.recording_microphone):
                        self.selected_microphone_position = (self.selected_microphone_position - 1) % len(
                            self.microphone_devices)
                elif self.current_view == 'AUDIO' and (
                        self.mic_next_rect.collidepoint(click_x, click_y) or self.mic_device_rect.collidepoint(click_x,
                                                                                                               click_y)):
                    if self.microphone_devices and (not self.recording_microphone):
                        self.selected_microphone_position = (self.selected_microphone_position + 1) % len(
                            self.microphone_devices)
                elif self.current_view == 'AUDIO' and self.import_audio_rect.collidepoint(click_x, click_y):
                    self.choose_and_import_file()
                elif self.current_view == 'AUDIO' and self.record_audio_rect.collidepoint(click_x, click_y):
                    if self.recording_microphone:
                        self.stop_microphone_recording()
                    else:
                        self.start_microphone_recording()

                # Eventos de Clique no Sequenciador de Bateria
                elif self.current_view == 'SEQUENCER':
                    for track_idx, track in enumerate(self.drum_tracks):
                        y = self.track_start_y + track_idx * self.row_height
                        for step in range(16):
                            x = self.sequencer_start_x + step * (self.step_size + self.step_gap)
                            rect = pygame.Rect(x, y + 16, self.step_size, self.step_size)
                            if rect.collidepoint(click_x, click_y):
                                track['pattern'][step] = not track['pattern'][step]
                                if track['pattern'][step]:
                                    sound_key = track['name']
                                    raw_wave = self.drum_sounds_map.get(f"{sound_key}_WAVE")
                                    if raw_wave is not None:
                                        processed_wave = track['mixer_channel'].process_audio(raw_wave)
                                        sound = make_sound(processed_wave)
                                    else:
                                        sound = self.drum_sounds_map[sound_key]
                                    self.play_sound_from_mixer(sound, track['mixer_channel'])
                                break

                # Eventos de Clique no Piano Roll (Notas Melódicas)
                elif self.current_view == 'PIANO':
                    clicked_something = False
                    for visible_row in range(self.visible_piano_rows):
                        note_index = self.piano_scroll + visible_row
                        if note_index >= len(piano_notes):
                            continue
                        note_name = piano_notes[note_index]
                        y = self.piano_grid_top + visible_row * self.piano_row_height

                        # Clicar na Tecla Virtual do Piano (Toca uma prévia rápida usando o synth ativo!)
                        key_rect = pygame.Rect(20, y, 100, self.piano_row_height)
                        if key_rect.collidepoint(click_x, click_y):
                            current_track = self.instrument_tracks[self.active_instrument_track_index]
                            freq = self.melody_synth.note_frequency(note_name)
                            step_duration_sec = 60.0 / self.bpm / 4.0
                            preview_wave = current_track.synth.generate_wave(freq, step_duration_sec, 44100, 1.0)
                            processed_wave = current_track.mixer_channel.process_audio(preview_wave)
                            self.play_sound_from_mixer(make_sound(processed_wave), current_track.mixer_channel)
                            clicked_something = True
                            break

                        # Clicar na Grade de Passos
                        for step in range(16):
                            actual_step = self.piano_page * 16 + step
                            x = self.piano_grid_start_x + step * self.piano_step_width
                            cell_rect = pygame.Rect(x, y, self.piano_step_width, self.piano_row_height)
                            if cell_rect.collidepoint(click_x, click_y):
                                current_track = self.instrument_tracks[self.active_instrument_track_index]
                                current_note = current_track.pattern[note_index][actual_step]
                                if current_note is not None:
                                    current_track.clear_note_at(note_index, actual_step)
                                else:
                                    new_note = Note(pitch=note_name, instrument=current_track.synth.name)
                                    current_track.set_note_at(note_index, actual_step, new_note)
                                    freq = self.melody_synth.note_frequency(note_name)
                                    step_duration_sec = 60.0 / self.bpm / 4.0
                                    preview_wave = current_track.synth.generate_wave(freq, step_duration_sec, 44100,
                                                                                     1.0)
                                    processed_wave = current_track.mixer_channel.process_audio(preview_wave)
                                    self.play_sound_from_mixer(make_sound(processed_wave), current_track.mixer_channel)
                                clicked_something = True
                                break

                    if not clicked_something:
                        # Seletor de Instrumentos (Abas no rodapé do Piano Roll)
                        instrument_y = 585
                        for idx, track in enumerate(self.instrument_tracks):
                            rect = pygame.Rect(130 + idx * 100, instrument_y, 85, 30)
                            if rect.collidepoint(click_x, click_y):
                                self.active_instrument_track_index = idx
                                clicked_something = True
                                break

                        if not clicked_something:
                            # Clicar no botão "+" de adicionar pista melódica de sintetizador dinâmico
                            add_rect = pygame.Rect(130 + len(self.instrument_tracks) * 100, instrument_y, 40, 30)
                            if add_rect.collidepoint(click_x, click_y):
                                clicked_something = True
                                # Carregamento dinâmico de classe de sintetizador personalizado
                                root = tk.Tk()
                                root.withdraw()
                                root.attributes('-topmost', True)
                                path = filedialog.askopenfilename(
                                    title='Carregar Sintetizador Personalizado (.py)',
                                    filetypes=[('Arquivos Python', '*.py')]
                                )
                                root.destroy()
                                if path:
                                    try:
                                        import importlib.util
                                        import inspect
                                        from base_synth import BaseSynthesizer

                                        module_name = os.path.basename(path)[:-3]
                                        spec = importlib.util.spec_from_file_location(module_name, path)
                                        if spec is not None and spec.loader is not None:
                                            module = importlib.util.module_from_spec(spec)
                                            spec.loader.exec_module(module)

                                            synth_class = None
                                            for m_name, obj in inspect.getmembers(module, inspect.isclass):
                                                if issubclass(obj, BaseSynthesizer) and obj is not BaseSynthesizer:
                                                    synth_class = obj
                                                    break

                                            if synth_class:
                                                novo_synth = synth_class()
                                                nova_trilha = InstrumentTrack(name=novo_synth.name, synth=novo_synth,
                                                                              num_steps=32)
                                                init_channel_fx(nova_trilha.mixer_channel)
                                                self.instrument_tracks.append(nova_trilha)
                                                self.active_instrument_track_index = len(self.instrument_tracks) - 1
                                                print(f"Sintetizador '{novo_synth.name}' carregado dinamicamente!")
                                            else:
                                                print(
                                                    "Nenhum sintetizador herdado de BaseSynthesizer encontrado no arquivo.")
                                    except Exception as err:
                                        print("Falha ao carregar sintetizador personalizado:", err)

                        # Processa cliques nos botões de paginação do Piano Roll
                        if not clicked_something:
                            if self.piano_page1_rect.collidepoint(click_x, click_y):
                                self.piano_page = 0
                                clicked_something = True
                            elif self.piano_page2_rect.collidepoint(click_x, click_y):
                                self.piano_page = 1
                                clicked_something = True
                            elif self.piano_follow_rect.collidepoint(click_x, click_y):
                                self.piano_auto_follow = not self.piano_auto_follow
                                clicked_something = True

                # Mixer de Canais (Interações)
                elif self.current_view == 'MIXER':
                    mixer_tracks = []
                    for track in self.drum_tracks:
                        mixer_tracks.append((track['name'], track['mixer_channel']))
                    for track in self.instrument_tracks:
                        mixer_tracks.append((track.name, track.mixer_channel))
                    for track in self.audio_tracks:
                        mixer_tracks.append((track.name, track.mixer_channel))

                    strip_width = 105
                    strip_start_x = 20
                    strip_top = 225

                    for i, (name, channel) in enumerate(mixer_tracks[:9]):
                        x = strip_start_x + i * strip_width

                        mute_rect = pygame.Rect(x + 12, strip_top + 28, 34, 26)
                        solo_rect = pygame.Rect(x + 54, strip_top + 28, 34, 26)
                        volume_rect = pygame.Rect(x + 45, strip_top + 162, 14, 130)
                        pan_rect = pygame.Rect(x + 12, strip_top + 325, 76, 18)

                        # Nova grade de FX de 2x4 posições
                        fx_positions = [
                            (x + 11, strip_top + 58),  # Slot 0
                            (x + 49, strip_top + 58),  # Slot 1
                            (x + 11, strip_top + 82),  # Slot 2
                            (x + 49, strip_top + 82),  # Slot 3
                            (x + 11, strip_top + 106),  # Slot 4
                            (x + 49, strip_top + 106),  # Slot 5
                            (x + 11, strip_top + 130),  # Slot 6
                            (x + 49, strip_top + 130)  # Slot 7
                        ]

                        clicked_fx = False
                        for idx, (fx_x, fx_y) in enumerate(fx_positions):
                            fx_rect = pygame.Rect(fx_x, fx_y, 36, 20)
                            if fx_rect.collidepoint(click_x, click_y):
                                clicked_fx = True
                                if idx < len(channel.effects_chain):
                                    plugin = channel.effects_chain[idx]
                                    if idx == 7 and plugin.name == "":
                                        # Carregamento dinâmico de plugin no slot 8
                                        root = tk.Tk()
                                        root.withdraw()
                                        root.attributes('-topmost', True)
                                        path = filedialog.askopenfilename(
                                            title='Carregar Plugin Personalizado (.py)',
                                            filetypes=[('Arquivos Python', '*.py')]
                                        )
                                        root.destroy()
                                        if path:
                                            try:
                                                import importlib.util
                                                import inspect
                                                from plugins import AudioPlugin

                                                module_name = os.path.basename(path)[:-3]
                                                spec = importlib.util.spec_from_file_location(module_name, path)
                                                if spec is not None and spec.loader is not None:
                                                    module = importlib.util.module_from_spec(spec)
                                                    spec.loader.exec_module(module)

                                                    plugin_class = None
                                                    for m_name, obj in inspect.getmembers(module, inspect.isclass):
                                                        if issubclass(obj, AudioPlugin) and obj is not AudioPlugin:
                                                            plugin_class = obj
                                                            break

                                                    if plugin_class:
                                                        novo_plugin = plugin_class()
                                                        novo_plugin.enabled = True
                                                        channel.effects_chain[7] = novo_plugin
                                                        print(
                                                            f"Plugin '{novo_plugin.name}' carregado dinamicamente no canal {channel.name}!")
                                                    else:
                                                        print("Nenhum plugin herdado de AudioPlugin encontrado.")
                                            except Exception as err:
                                                print("Falha ao carregar plugin dinâmico:", err)
                                    else:
                                        plugin.enabled = not plugin.enabled
                                break

                        if clicked_fx:
                            break
                        elif mute_rect.collidepoint(click_x, click_y):
                            channel.muted = not channel.muted
                            break
                        elif solo_rect.collidepoint(click_x, click_y):
                            channel.solo = not channel.solo
                            break
                        elif volume_rect.inflate(18, 0).collidepoint(click_x, click_y):
                            self.mixer_drag = (channel, 'volume', volume_rect)
                            ratio = (volume_rect.bottom - click_y) / volume_rect.height
                            channel.volume = max(0.0, min(1.0, ratio))
                            break
                        elif pan_rect.inflate(0, 10).collidepoint(click_x, click_y):
                            self.mixer_drag = (channel, 'pan', pan_rect)
                            ratio = (click_x - pan_rect.left) / pan_rect.width
                            channel.pan = max(-1.0, min(1.0, ratio * 2.0 - 1.0))
                            break

                # Interações de Mover Waveform e Mute/Solo no Audio Tab
                elif self.current_view == 'AUDIO':
                    for index, track in enumerate(self.audio_tracks):
                        y = 270 + index * 72
                        mute_rect = pygame.Rect(30, y + 20, 30, 25)
                        delete_rect = pygame.Rect(70, y + 20, 30, 25)

                        loop_duration = 60 / self.bpm / 4 * 32
                        clip_width = int(track.length / loop_duration * 740)
                        clip_width = max(50, min(740, clip_width))
                        clip_x = 210 + int(track.start_step / 32 * 740)
                        clip_rect = pygame.Rect(clip_x, y + 10, clip_width, 48)

                        if mute_rect.collidepoint(click_x, click_y):
                            track.mixer_channel.muted = not track.mixer_channel.muted
                            break
                        elif delete_rect.collidepoint(click_x, click_y):
                            del self.audio_tracks[index]
                            break
                        elif clip_rect.collidepoint(click_x, click_y):
                            self.dragging_audio = index
                            break

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging_audio = None
                self.mixer_drag = None

            elif event.type == pygame.MOUSEMOTION:
                motion_x, motion_y = event.pos
                if self.mixer_drag is not None:
                    channel, control_type, control_rect = self.mixer_drag
                    if control_type == 'volume':
                        ratio = (control_rect.bottom - motion_y) / control_rect.height
                        channel.volume = max(0.0, min(1.0, ratio))
                    elif control_type == 'pan':
                        ratio = (motion_x - control_rect.left) / control_rect.width
                        channel.pan = max(-1.0, min(1.0, ratio * 2.0 - 1.0))

                elif self.dragging_audio is not None and self.dragging_audio < len(self.audio_tracks):
                    relative_x = motion_x - 210
                    ratio = relative_x / 740
                    ratio = max(0, min(0.999, ratio))
                    new_step = int(ratio * 32)
                    self.audio_tracks[self.dragging_audio].start_step = new_step

        return True

    def update_sequencer_ticks(self, now: int):
        """Monitora e avança as etapas do playhead baseadas no tempo real e BPM."""
        if self.playing:
            while now >= self.next_step_time:
                self.current_step += 1
                if self.current_step >= 32:
                    self.current_step = 0
                if self.piano_auto_follow:
                    self.piano_page = self.current_step // 16

                # Despara os sons correspondentes ao passo atual
                self.sequencer.play_step(
                    self.current_step, self.bpm, self.drum_tracks, self.instrument_tracks,
                    self.audio_tracks, self.drum_sounds_map, self.melody_synth, self.get_all_channels()
                )
                step_interval = 60000 / self.bpm / 4
                self.next_step_time += step_interval

    def draw_layout(self):
        """Renderiza visualmente todos os botões, trilhas e painéis na janela Pygame."""
        self.screen.fill(BACKGROUND)
        mouse_pos = pygame.mouse.get_pos()
        piano_notes = get_piano_notes()

        # Título da DAW
        title = title_font.render('OndaKraft', True, TEXT_COLOR)
        self.screen.blit(title, (25, 18))
        pygame.draw.line(self.screen, LINE_COLOR, (0, 68), (WIDTH, 68), 1)

        # Botões de Play / Stop / BPM do Painel de Transporte
        pygame.draw.rect(self.screen, BUTTON_BACKGROUND, self.play_rect)
        pygame.draw.rect(self.screen, LINE_COLOR, self.play_rect, 2)
        pygame.draw.polygon(self.screen, GREEN, [(53, 91), (53, 115), (79, 103)])

        pygame.draw.rect(self.screen, BUTTON_BACKGROUND, self.stop_rect)
        pygame.draw.rect(self.screen, LINE_COLOR, self.stop_rect, 2)
        pygame.draw.rect(self.screen, RED, (140, 92, 20, 20))

        pygame.draw.rect(self.screen, BUTTON_BACKGROUND, self.bpm_minus_rect)
        pygame.draw.rect(self.screen, LINE_COLOR, self.bpm_minus_rect, 2)
        minus_text = small_font.render('-', True, TEXT_COLOR)
        self.screen.blit(minus_text, minus_text.get_rect(center=self.bpm_minus_rect.center))

        pygame.draw.rect(self.screen, BUTTON_BACKGROUND, self.bpm_rect)
        pygame.draw.rect(self.screen, LINE_COLOR, self.bpm_rect, 2)
        bpm_val_text = small_font.render(str(self.bpm), True, TEXT_COLOR)
        self.screen.blit(bpm_val_text, bpm_val_text.get_rect(center=self.bpm_rect.center))

        pygame.draw.rect(self.screen, BUTTON_BACKGROUND, self.bpm_plus_rect)
        pygame.draw.rect(self.screen, LINE_COLOR, self.bpm_plus_rect, 2)
        plus_text = small_font.render('+', True, TEXT_COLOR)
        self.screen.blit(plus_text, plus_text.get_rect(center=self.bpm_plus_rect.center))

        bpm_label = small_font.render('BPM', True, TEXT_COLOR)
        self.screen.blit(bpm_label, (365, 93))
        pygame.draw.line(self.screen, LINE_COLOR, (0, 140), (WIDTH, 140), 1)

        # Definição de Cores Ativas de Aba
        sequencer_color = TEXT_COLOR if self.current_view == 'SEQUENCER' else SECONDARY_TEXT
        piano_color = TEXT_COLOR if self.current_view == 'PIANO' else SECONDARY_TEXT
        audio_color = TEXT_COLOR if self.current_view == 'AUDIO' else SECONDARY_TEXT
        mixer_color = TEXT_COLOR if self.current_view == 'MIXER' else SECONDARY_TEXT

        # Desenho dos Rótulos das Abas
        seq_text_surface = section_font.render('SEQUENCER', True, sequencer_color)
        piano_text_surface = section_font.render('PIANO ROLL', True, piano_color)
        audio_text_surface = section_font.render('AUDIO TIMELINE', True, audio_color)
        mixer_text_surface = section_font.render('MIXER', True, mixer_color)

        self.screen.blit(seq_text_surface, (35, 155))
        self.screen.blit(piano_text_surface, (185, 155))
        self.screen.blit(audio_text_surface, (335, 155))
        self.screen.blit(mixer_text_surface, (545, 155))

        # Botões de Ação Globais (SAVE, LOAD, EXPORT)
        pygame.draw.rect(self.screen, BUTTON_BACKGROUND, self.save_project_rect)
        pygame.draw.rect(self.screen, LINE_COLOR, self.save_project_rect, 1)
        pygame.draw.rect(self.screen, BUTTON_BACKGROUND, self.load_project_rect)
        pygame.draw.rect(self.screen, LINE_COLOR, self.load_project_rect, 1)
        pygame.draw.rect(self.screen, BUTTON_BACKGROUND, self.export_project_rect)
        pygame.draw.rect(self.screen, LINE_COLOR, self.export_project_rect, 1)

        save_lbl = tiny_font.render('SAVE', True, TEXT_COLOR)
        load_lbl = tiny_font.render('LOAD', True, TEXT_COLOR)
        export_lbl = tiny_font.render('EXPORT', True, BLUE)

        self.screen.blit(save_lbl, save_lbl.get_rect(center=self.save_project_rect.center))
        self.screen.blit(load_lbl, load_lbl.get_rect(center=self.load_project_rect.center))
        self.screen.blit(export_lbl, export_lbl.get_rect(center=self.export_project_rect.center))

        # Linhas de realce da aba ativa
        if self.current_view == 'SEQUENCER':
            pygame.draw.line(self.screen, BLUE, (35, 185), (153, 185), 3)
        elif self.current_view == 'PIANO':
            pygame.draw.line(self.screen, BLUE, (185, 185), (305, 185), 3)
        elif self.current_view == 'AUDIO':
            pygame.draw.line(self.screen, BLUE, (335, 185), (515, 185), 3)
        else:
            pygame.draw.line(self.screen, BLUE, (545, 185), (610, 185), 3)

        pygame.draw.line(self.screen, LINE_COLOR, (0, 198), (WIDTH, 198), 1)

        # ------------------- VIEW: SEQUENCER (BATERIA) -------------------
        if self.current_view == 'SEQUENCER':
            # Numeração dos passos (1 a 16)
            for step in range(16):
                x = self.sequencer_start_x + step * (self.step_size + self.step_gap)
                num_lbl = step_font.render(str(step + 1), True, TEXT_COLOR)
                self.screen.blit(num_lbl, num_lbl.get_rect(center=(x + self.step_size // 2, 216)))

            # Playhead Vertical
            if self.playing:
                playhead_x = self.sequencer_start_x + self.current_step * (self.step_size + self.step_gap)
                pygame.draw.line(self.screen, PLAYHEAD_BLUE, (playhead_x + self.step_size // 2, 225),
                                 (playhead_x + self.step_size // 2, 575), 3)

            # Linhas de Pistas de Bateria
            for track_idx, track in enumerate(self.drum_tracks):
                y = self.track_start_y + track_idx * self.row_height
                pygame.draw.line(self.screen, LINE_COLOR, (20, y + 60), (WIDTH - 20, y + 60), 1)

                # Desenha o Ícone e Rótulo da Pista
                self.screen.blit(drum_images[track_idx], (30, y + 6))
                lbl_name = track_font.render(track['name'], True, TEXT_COLOR)
                self.screen.blit(lbl_name, (95, y + 20))

                # Desenha a grade de 16 botões
                for step in range(16):
                    x = self.sequencer_start_x + step * (self.step_size + self.step_gap)
                    rect = pygame.Rect(x, y + 16, self.step_size, self.step_size)

                    if track['pattern'][step]:
                        cell_color = GREEN
                        if rect.collidepoint(mouse_pos):
                            cell_color = GREEN_HOVER
                    else:
                        cell_color = STEP_BACKGROUND
                        if rect.collidepoint(mouse_pos):
                            cell_color = STEP_HOVER

                    pygame.draw.rect(self.screen, cell_color, rect)
                    pygame.draw.rect(self.screen, LINE_COLOR, rect, 2)

        # ------------------- VIEW: PIANO ROLL (MELODIA) -------------------
        elif self.current_view == 'PIANO':
            # Numeração dos passos na grade melódica (com offset de página)
            for step in range(16):
                x = self.piano_grid_start_x + step * self.piano_step_width
                actual_step_num = step + 1 + self.piano_page * 16
                num_lbl = step_font.render(str(actual_step_num), True, TEXT_COLOR)
                self.screen.blit(num_lbl, num_lbl.get_rect(center=(x + self.piano_step_width // 2, 213)))

            # Grade de Teclas do Piano
            for visible_row in range(self.visible_piano_rows):
                note_index = self.piano_scroll + visible_row
                if note_index >= len(piano_notes):
                    continue
                note_name = piano_notes[note_index]
                y = self.piano_grid_top + visible_row * self.piano_row_height

                is_sharp = '#' in note_name
                key_rect = pygame.Rect(20, y, 100, self.piano_row_height)

                key_color = BLACK_KEY if is_sharp else WHITE_KEY
                txt_color = (240, 240, 240) if is_sharp else TEXT_COLOR

                pygame.draw.rect(self.screen, key_color, key_rect)
                pygame.draw.rect(self.screen, LINE_COLOR, key_rect, 1)

                note_lbl = tiny_font.render(note_name, True, txt_color)
                self.screen.blit(note_lbl, (35, y + 7))

                # Grade de Células de Passo (Com offset de página ativa)
                for step in range(16):
                    x = self.piano_grid_start_x + step * self.piano_step_width
                    cell_rect = pygame.Rect(x, y, self.piano_step_width, self.piano_row_height)

                    actual_step = step + self.piano_page * 16
                    current_track = self.instrument_tracks[self.active_instrument_track_index]
                    note_obj = current_track.pattern[note_index][actual_step]
                    if note_obj is not None:
                        inst = note_obj.instrument
                        cell_color = self.INSTRUMENT_COLORS.get(inst, BLUE)
                        if cell_rect.collidepoint(mouse_pos):
                            cell_color = self.INSTRUMENT_HOVER_COLORS.get(inst, PLAYHEAD_BLUE)
                    else:
                        cell_color = (232, 232, 228) if is_sharp else (248, 248, 245)
                        if cell_rect.collidepoint(mouse_pos):
                            cell_color = STEP_HOVER

                    pygame.draw.rect(self.screen, cell_color, cell_rect)
                    pygame.draw.rect(self.screen, LIGHT_LINE, cell_rect, 1)

            # Playhead Vertical do Piano Roll (Apenas se pertencer à página ativa)
            if self.playing:
                playhead_page = self.current_step // 16
                if playhead_page == self.piano_page:
                    local_step = self.current_step % 16
                    playhead_x = self.piano_grid_start_x + local_step * self.piano_step_width
                    pygame.draw.line(self.screen, PLAYHEAD_BLUE, (playhead_x, self.piano_grid_top), (playhead_x,
                                                                                                     self.piano_grid_top + self.visible_piano_rows * self.piano_row_height),
                                     3)

            # Seletor de Instrumento Melódico Ativo (Sub-abas dinâmicas de instrumento)
            instrument_y = 585
            for idx, track in enumerate(self.instrument_tracks):
                rect = pygame.Rect(130 + idx * 100, instrument_y, 85, 30)
                if self.active_instrument_track_index == idx:
                    pygame.draw.rect(self.screen, self.INSTRUMENT_COLORS.get(track.synth.name, BLUE), rect)
                    text_color = (255, 255, 255)
                else:
                    pygame.draw.rect(self.screen, BUTTON_BACKGROUND, rect)
                    text_color = TEXT_COLOR
                pygame.draw.rect(self.screen, LINE_COLOR, rect, 1)

                inst_lbl = tiny_font.render(track.name[:10], True, text_color)
                self.screen.blit(inst_lbl, inst_lbl.get_rect(center=rect.center))

            # Desenha botão "+" para adicionar sintetizador dinâmico
            add_rect = pygame.Rect(130 + len(self.instrument_tracks) * 100, instrument_y, 40, 30)
            pygame.draw.rect(self.screen, BUTTON_BACKGROUND, add_rect)
            pygame.draw.rect(self.screen, LINE_COLOR, add_rect, 1)
            plus_lbl = tiny_font.render("+", True, TEXT_COLOR)
            self.screen.blit(plus_lbl, plus_lbl.get_rect(center=add_rect.center))

            # --- Desenha os Botões de Paginação do Piano Roll (32 passos) ---
            # Botão Compasso 1
            if self.piano_page == 0:
                pygame.draw.rect(self.screen, PLAYHEAD_BLUE, self.piano_page1_rect)
                p1_txt_color = (255, 255, 255)
            else:
                pygame.draw.rect(self.screen, BUTTON_BACKGROUND, self.piano_page1_rect)
                p1_txt_color = TEXT_COLOR
            pygame.draw.rect(self.screen, LINE_COLOR, self.piano_page1_rect, 1)
            p1_lbl = tiny_font.render("COMP. 1", True, p1_txt_color)
            self.screen.blit(p1_lbl, p1_lbl.get_rect(center=self.piano_page1_rect.center))

            # Botão Compasso 2
            if self.piano_page == 1:
                pygame.draw.rect(self.screen, PLAYHEAD_BLUE, self.piano_page2_rect)
                p2_txt_color = (255, 255, 255)
            else:
                pygame.draw.rect(self.screen, BUTTON_BACKGROUND, self.piano_page2_rect)
                p2_txt_color = TEXT_COLOR
            pygame.draw.rect(self.screen, LINE_COLOR, self.piano_page2_rect, 1)
            p2_lbl = tiny_font.render("COMP. 2", True, p2_txt_color)
            self.screen.blit(p2_lbl, p2_lbl.get_rect(center=self.piano_page2_rect.center))

            # Botão Auto-Follow
            if self.piano_auto_follow:
                pygame.draw.rect(self.screen, GREEN, self.piano_follow_rect)
                follow_txt_color = (255, 255, 255)
                follow_txt = "AUTO-FOLLOW: ON"
            else:
                pygame.draw.rect(self.screen, BUTTON_BACKGROUND, self.piano_follow_rect)
                follow_txt_color = SECONDARY_TEXT
                follow_txt = "AUTO-FOLLOW: OFF"
            pygame.draw.rect(self.screen, LINE_COLOR, self.piano_follow_rect, 1)
            follow_lbl = tiny_font.render(follow_txt, True, follow_txt_color)
            self.screen.blit(follow_lbl, follow_lbl.get_rect(center=self.piano_follow_rect.center))

        # ------------------- VIEW: AUDIO TIMELINE (SAMPLES) -------------------
        elif self.current_view == 'AUDIO':
            # Seletor de Microfone Integrado
            pygame.draw.rect(self.screen, BUTTON_BACKGROUND, self.mic_prev_rect)
            pygame.draw.rect(self.screen, LINE_COLOR, self.mic_prev_rect, 1)
            pygame.draw.rect(self.screen, BUTTON_BACKGROUND, self.mic_device_rect)
            pygame.draw.rect(self.screen, LINE_COLOR, self.mic_device_rect, 1)
            pygame.draw.rect(self.screen, BUTTON_BACKGROUND, self.mic_next_rect)
            pygame.draw.rect(self.screen, LINE_COLOR, self.mic_next_rect, 1)

            self.screen.blit(small_font.render('<', True, TEXT_COLOR),
                             small_font.render('<', True, TEXT_COLOR).get_rect(center=self.mic_prev_rect.center))
            self.screen.blit(small_font.render('>', True, TEXT_COLOR),
                             small_font.render('>', True, TEXT_COLOR).get_rect(center=self.mic_next_rect.center))

            _, active_mic_name = self.get_selected_microphone()
            # Corta nomes muito compridos para caber na caixa
            mic_w, _ = tiny_font.size('MIC: ' + active_mic_name)
            while mic_w > self.mic_device_rect.width - 18 and len(active_mic_name) > 4:
                active_mic_name = active_mic_name[:-1]
                mic_w, _ = tiny_font.size('MIC: ' + active_mic_name)
            if active_mic_name != self.get_selected_microphone()[1]:
                active_mic_name = active_mic_name[:-3] + '...'

            mic_text_surf = tiny_font.render('MIC: ' + active_mic_name, True, TEXT_COLOR)
            self.screen.blit(mic_text_surf, mic_text_surf.get_rect(center=self.mic_device_rect.center))

            # Botões de Importação e Gravação
            pygame.draw.rect(self.screen, BUTTON_BACKGROUND, self.import_audio_rect)
            pygame.draw.rect(self.screen, LINE_COLOR, self.import_audio_rect, 2)
            import_lbl = tiny_font.render('IMPORT', True, TEXT_COLOR)
            self.screen.blit(import_lbl, import_lbl.get_rect(center=self.import_audio_rect.center))

            btn_rec_color = RED if self.recording_microphone else BUTTON_BACKGROUND
            pygame.draw.rect(self.screen, btn_rec_color, self.record_audio_rect)
            pygame.draw.rect(self.screen, LINE_COLOR, self.record_audio_rect, 2)

            lbl_record = 'STOP' if self.recording_microphone else 'MIC'
            txt_record_surf = tiny_font.render(lbl_record, True, TEXT_COLOR)
            icon_x = self.record_audio_rect.x + 8
            icon_y = self.record_audio_rect.centery - microphone_image.get_height() // 2

            self.screen.blit(microphone_image, (icon_x, icon_y))
            txt_rec_rect = txt_record_surf.get_rect(
                midleft=(icon_x + microphone_image.get_width() + 5, self.record_audio_rect.centery))
            self.screen.blit(txt_record_surf, txt_rec_rect)

            # Linhas da Grade de Timeline do Áudio (32 passos)
            for step in range(32):
                x = 210 + int(step / 32 * 740)
                pygame.draw.line(self.screen, LIGHT_LINE, (x, 255), (x, HEIGHT - 25), 1)
                if step % 2 == 0:
                    step_lbl = tiny_font.render(str(step + 1), True, SECONDARY_TEXT)
                    self.screen.blit(step_lbl, (x + 4, 238))

            # Playhead da Timeline
            if self.playing:
                playhead_x = 210 + int(self.current_step / 32 * 740)
                pygame.draw.line(self.screen, PLAYHEAD_BLUE, (playhead_x, 255), (playhead_x, HEIGHT - 20), 3)

            # Renderiza as pistas de áudio físicas e formas de onda
            for index, track in enumerate(self.audio_tracks):
                y = 270 + index * 72
                pygame.draw.line(self.screen, LIGHT_LINE, (20, y + 62), (WIDTH - 20, y + 62), 1)

                # Mute e Delete
                mute_rect = pygame.Rect(30, y + 20, 30, 25)
                delete_rect = pygame.Rect(70, y + 20, 30, 25)

                mute_color = RED if track.mixer_channel.muted else BUTTON_BACKGROUND
                pygame.draw.rect(self.screen, mute_color, mute_rect)
                pygame.draw.rect(self.screen, LINE_COLOR, mute_rect, 1)

                mute_lbl = tiny_font.render('M', True, TEXT_COLOR)
                self.screen.blit(mute_lbl, mute_lbl.get_rect(center=mute_rect.center))

                pygame.draw.rect(self.screen, BUTTON_BACKGROUND, delete_rect)
                pygame.draw.rect(self.screen, LINE_COLOR, delete_rect, 1)

                del_lbl = tiny_font.render('X', True, RED)
                self.screen.blit(del_lbl, del_lbl.get_rect(center=delete_rect.center))

                name_lbl = tiny_font.render(track.name[:16], True, TEXT_COLOR)
                self.screen.blit(name_lbl, (108, y + 25))

                # Desenha o Clipe de Áudio Redimensionável na Timeline
                loop_duration = 60 / self.bpm / 4 * 32
                clip_width = int(track.length / loop_duration * 740)
                clip_width = max(50, min(740, clip_width))
                clip_x = 210 + int(track.start_step / 32 * 740)
                clip_rect = pygame.Rect(clip_x, y + 10, clip_width, 48)

                pygame.draw.rect(self.screen, (240, 220, 195), clip_rect)
                pygame.draw.rect(self.screen, ORANGE, clip_rect, 2)

                # Chama a renderização do NumPy encapsulada dentro do AudioTrack
                track.draw_waveform(self.screen, clip_rect.inflate(-6, -6), ORANGE)

        # ------------------- VIEW: MIXER (CONSOLES) -------------------
        elif self.current_view == 'MIXER':
            mixer_tracks = []
            for track in self.drum_tracks:
                mixer_tracks.append((track['name'], track['mixer_channel']))
            for track in self.instrument_tracks:
                mixer_tracks.append((track.name, track.mixer_channel))
            for track in self.audio_tracks:
                mixer_tracks.append((track.name, track.mixer_channel))

            strip_width = 105
            strip_start_x = 20
            strip_top = 225

            header = small_font.render('MESA DE MIXAGEM DA DAW (ATÉ 9 CANAIS)', True, TEXT_COLOR)
            self.screen.blit(header, (20, 207))

            for i, (name, channel) in enumerate(mixer_tracks[:9]):
                x = strip_start_x + i * strip_width
                strip_rect = pygame.Rect(x, strip_top, 96, 390)

                pygame.draw.rect(self.screen, BUTTON_BACKGROUND, strip_rect)
                pygame.draw.rect(self.screen, LIGHT_LINE, strip_rect, 1)

                # Rótulo de Nome do Canal
                name_surf = tiny_font.render(name[:11], True, TEXT_COLOR)
                self.screen.blit(name_surf, name_surf.get_rect(center=(x + 48, strip_top + 15)))

                # Mute & Solo
                mute_rect = pygame.Rect(x + 12, strip_top + 28, 34, 26)
                solo_rect = pygame.Rect(x + 54, strip_top + 28, 34, 26)

                mute_color = RED if channel.muted else BUTTON_BACKGROUND
                solo_color = GREEN if channel.solo else BUTTON_BACKGROUND

                pygame.draw.rect(self.screen, mute_color, mute_rect)
                pygame.draw.rect(self.screen, LINE_COLOR, mute_rect, 1)
                pygame.draw.rect(self.screen, solo_color, solo_rect)
                pygame.draw.rect(self.screen, LINE_COLOR, solo_rect, 1)

                self.screen.blit(tiny_font.render('M', True, TEXT_COLOR),
                                 tiny_font.render('M', True, TEXT_COLOR).get_rect(center=mute_rect.center))
                self.screen.blit(tiny_font.render('S', True, TEXT_COLOR),
                                 tiny_font.render('S', True, TEXT_COLOR).get_rect(center=solo_rect.center))

                # Nova grade de FX de 2x4 posições
                fx_positions = [
                    (x + 11, strip_top + 58),  # Slot 0
                    (x + 49, strip_top + 58),  # Slot 1
                    (x + 11, strip_top + 82),  # Slot 2
                    (x + 49, strip_top + 82),  # Slot 3
                    (x + 11, strip_top + 106),  # Slot 4
                    (x + 49, strip_top + 106),  # Slot 5
                    (x + 11, strip_top + 130),  # Slot 6
                    (x + 49, strip_top + 130)  # Slot 7
                ]

                labels_map = {
                    "Delay": "DLY",
                    "Tremolo": "TRM",
                    "Distortion": "DST",
                    "Reverb": "RVB",
                    "EQ": "EQ",
                    "Compressor": "CMP",
                    "Chorus": "CHO"
                }

                for idx, (fx_x, fx_y) in enumerate(fx_positions):
                    fx_rect = pygame.Rect(fx_x, fx_y, 36, 20)
                    if idx < len(channel.effects_chain):
                        plugin = channel.effects_chain[idx]
                        p_name = plugin.name

                        if p_name == "":
                            lbl_text = "+"
                        else:
                            lbl_text = labels_map.get(p_name, p_name[:3].upper())

                        # Determina a cor com base no estado de ativação
                        if plugin.enabled:
                            btn_color = PURPLE
                            txt_color = (255, 255, 255)
                        else:
                            btn_color = BUTTON_BACKGROUND
                            txt_color = SECONDARY_TEXT

                        pygame.draw.rect(self.screen, btn_color, fx_rect)
                        pygame.draw.rect(self.screen, LINE_COLOR, fx_rect, 1)

                        fx_lbl_surf = tiny_font.render(lbl_text, True, txt_color)
                        self.screen.blit(fx_lbl_surf, fx_lbl_surf.get_rect(center=fx_rect.center))

                # Fader de Volume compactado (Deslizador vertical)
                volume_rect = pygame.Rect(x + 45, strip_top + 162, 14, 130)
                pygame.draw.rect(self.screen, LIGHT_LINE, volume_rect)

                vol = channel.volume
                knob_y = int(volume_rect.bottom - vol * volume_rect.height)
                pygame.draw.rect(self.screen, BLUE, pygame.Rect(x + 37, knob_y - 5, 30, 10))

                vol_val_lbl = tiny_font.render(str(int(vol * 100)), True, SECONDARY_TEXT)
                self.screen.blit(vol_val_lbl, vol_val_lbl.get_rect(center=(x + 52, strip_top + 305)))

                # Slider de Pan (Panorâmica Estéreo Esquerda/Direita)
                pan_rect = pygame.Rect(x + 12, strip_top + 325, 76, 18)
                pygame.draw.line(self.screen, LIGHT_LINE, (pan_rect.left, pan_rect.centery),
                                 (pan_rect.right, pan_rect.centery), 3)

                pan_val = channel.pan
                pan_x = int(pan_rect.left + (pan_val + 1.0) / 2.0 * pan_rect.width)
                pygame.draw.circle(self.screen, PURPLE, (pan_x, pan_rect.centery), 7)

                pan_lbl = tiny_font.render('PAN', True, SECONDARY_TEXT)
                self.screen.blit(pan_lbl, pan_lbl.get_rect(center=(x + 50, strip_top + 355)))

        # Atualiza a renderização
        pygame.display.update()

    def run(self):
        """Metodo de inicialização e controle do loop principal da DAW OndaKraft."""
        running = True
        while running:
            now = pygame.time.get_ticks()
            running = self.handle_pygame_events()
            self.update_sequencer_ticks(now)
            self.draw_layout()
            self.clock.tick(60)  # Grampeia em 60 FPS

        # Desliga de forma segura
        pygame.quit()


if __name__ == "__main__":
    app = OndaKraftApp()
    app.run()
