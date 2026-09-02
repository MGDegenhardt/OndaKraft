import numpy as np


    # Desenvolvimento de sintetizador de bateria baseado em equações matemáticas e processamento de sinal
    # MGDegenhardt, 2026 - OndaKraft (baseado no JRYBeats)

class DrumSynthesizer:
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

    def eq_noise(self, noise: np.ndarray, low_cut: float = 0, high_cut: float = None,
                 peak_freq: float = None, peak_gain: float = 0.0) -> np.ndarray:
        """Filtro de equalização espectral usando FFT [6]."""
        spectrum = np.fft.rfft(noise)
        frequencies = np.fft.rfftfreq(len(noise), 1 / self.sample_rate)
        shape = np.ones_like(frequencies)

        if low_cut > 0:
            shape *= np.clip(frequencies / low_cut, 0.0, 1.0)
        if high_cut is not None:
            shape *= np.clip(high_cut / np.maximum(frequencies, 1), 0.0, 1.0)
        if peak_freq is not None and peak_gain != 0:
            width = max(1.0, peak_freq * 0.55)
            bell = np.exp(-0.5 * ((frequencies - peak_freq) / width) ** 2)
            shape *= 1.0 + bell * peak_gain

        spectrum *= shape
        filtered = np.fft.irfft(spectrum, n=len(noise))
        peak = np.max(np.abs(filtered))
        if peak > 0:
            filtered /= peak
        return filtered

    def generate_kick(self) -> np.ndarray:
        """Gera bumbo com queda rápida exponencial [7]."""
        duration = 0.5
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
        frequency = 50 + 210 * np.exp(-35 * t)
        phase = 2 * np.pi * np.cumsum(frequency) / self.sample_rate

        kick_wave = np.sin(phase)
        kick_wave += 0.18 * np.sin(2 * phase)
        kick_wave *= np.exp(-7 * t)

        click = np.random.uniform(-1, 1, len(t))
        click *= np.exp(-100 * t)
        kick_wave += click * 0.12
        kick_wave *= 0.85
        return kick_wave

    def generate_snare(self) -> np.ndarray:
        """Gera caixa usando ruído filtrado por FFT [8]."""
        snare_duration = 0.32
        snare_t = np.linspace(0, snare_duration, int(self.sample_rate * snare_duration), endpoint=False)

        snare_noise = np.random.uniform(-1, 1, len(snare_t))
        snare_noise = self.eq_noise(snare_noise, low_cut=550, high_cut=9500, peak_freq=2400, peak_gain=1.2)

        snare_body = np.sin(2 * np.pi * 185 * snare_t)
        snare_body += 0.35 * np.sin(2 * np.pi * 330 * snare_t)

        noise_envelope = np.exp(-13 * snare_t)
        body_envelope = np.exp(-18 * snare_t)

        snare_attack = np.random.uniform(-1, 1, len(snare_t))
        snare_attack = self.eq_noise(snare_attack, low_cut=1800, high_cut=12000, peak_freq=4500, peak_gain=0.8)
        snare_attack *= np.exp(-90 * snare_t)

        snare_wave = snare_noise * noise_envelope * 0.72 + snare_body * body_envelope * 0.38 + snare_attack * 0.2
        snare_wave *= 0.75
        return snare_wave

    def generate_hihat(self) -> np.ndarray:
        """Gera chimbau de alta frequência e textura metálica [8]."""
        hihat_duration = 0.1
        hihat_t = np.linspace(0, hihat_duration, int(self.sample_rate * hihat_duration), endpoint=False)

        hihat_noise = np.random.uniform(-1, 1, len(hihat_t))
        hihat_noise = self.eq_noise(hihat_noise, low_cut=5500, high_cut=18000, peak_freq=10500, peak_gain=1.5)

        hihat_envelope = np.exp(-48 * hihat_t)
        hihat_wave = hihat_noise * hihat_envelope * 0.48

        for metallic_frequency in (6400, 7900, 10100, 12400):
            hihat_wave += np.sin(2 * np.pi * metallic_frequency * hihat_t) * np.exp(-55 * hihat_t) * 0.025
        return hihat_wave

    def generate_perc(self) -> np.ndarray:
        """Gera maracá curto [8]."""
        perc_duration = 0.12
        perc_t = np.linspace(0, perc_duration, int(self.sample_rate * perc_duration), endpoint=False)
        perc_noise = np.random.uniform(-1, 1, len(perc_t))
        perc_wave = perc_noise * np.exp(-28 * perc_t) * 0.35
        return perc_wave

    def generate_clap(self) -> np.ndarray:
        """Gera palmas acústicas com micro-impactos [9]."""
        clap_duration = 0.42
        clap_t = np.linspace(0, clap_duration, int(self.sample_rate * clap_duration), endpoint=False)

        clap_noise = np.random.uniform(-1, 1, len(clap_t))
        clap_noise = self.eq_noise(clap_noise, low_cut=900, high_cut=12500, peak_freq=3200, peak_gain=1.5)

        first_start = 0.0
        first_decay = 0.008
        first_burst = np.where(clap_t >= first_start, np.exp(-(clap_t - first_start) / first_decay), 0)
        first_burst *= clap_t < 0.025

        second_start = 0.022
        second_decay = 0.01
        second_burst = np.where(clap_t >= second_start, np.exp(-(clap_t - second_start) / second_decay), 0)
        second_burst *= clap_t < second_start + 0.03

        tail_start = 0.045
        tail = np.where(clap_t >= tail_start, np.exp(-(clap_t - tail_start) / 0.105), 0)

        clap_envelope = first_burst * 1.0 + second_burst * 0.95 + tail * 0.55
        clap_wave = clap_noise * clap_envelope

        clap_body = np.sin(2 * np.pi * 1150 * clap_t) + 0.5 * np.sin(2 * np.pi * 1750 * clap_t)
        clap_body *= np.where(clap_t >= tail_start, np.exp(-(clap_t - tail_start) / 0.055), 0)
        clap_wave += clap_body * 0.08

        second_texture = np.random.uniform(-1, 1, len(clap_t))
        second_texture = self.eq_noise(second_texture, low_cut=1200, high_cut=11000, peak_freq=4000, peak_gain=1.0)
        second_texture *= second_burst

        clap_wave += second_texture * 0.22
        clap_wave *= 0.72
        return clap_wave