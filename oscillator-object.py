import wave
import struct
import datetime

import abc
import math

import ctypes

SAMPLING_RATE = 44100
VOLUME_MAX = 32000
VOLUME_MIN = -32767
A4 = 440

class Oscillator(abc.ABC):
    # https://python.plainenglish.io/making-a-synth-with-python-oscillators-2cb8e68e9c3b
    def __init__(self, frequency=A4, phase=0, amplitude=1, sample_rate=SAMPLING_RATE, wave_range = (-1, 1)):
        self._frequency = frequency
        self._phase = phase
        self._amplitude = amplitude
        self._sample_rate = sample_rate
        self._wave_range = wave_range

        # changeables:
        self._f = self._frequency
        self._a = self._amplitude
        self._p = self._phase

    @property
    def init_frequency(self):
        return self._frequency

    @property
    def init_amplitude(self):
        return self._amplitude

    @property
    def init_phase(self):
        return self._phase

    @property
    def frequency(self):
        return self._f

    @frequency.setter
    def frequency(self, value):
        self._f = value
        self._post_freq_set()

    @property
    def amplitude(self):
        return self._a

    @amplitude.setter
    def amplitude(self, value):
        self._a = value
        self._post_amp_set()

    @property
    def phase(self):
        return self._p

    @phase.setter
    def phase(self, value):
        self._p = value
        self._post_phase_set()

    def _post_freq_set(self):
        pass

    def _post_amp_set(self):
        pass

    def _post_phase_set(self):
        pass

    @abc.abstractmethod
    def _initialize_osc(self):
        _pass

    @staticmethod
    def squish_value(value, min_value=0, max_value=1):
        return (((value + 1)/2) * (max_value - min_value)) + min_value

    @abc.abstractmethod
    def __next__(self):
        return None

    def __iter__(self):
        self.frequency = self._frequency
        self.phase = self._phase
        self.amplitude = self._amplitude
        self._initialize_osc()
        return self


class SineOscillator(Oscillator):
    def _post_freq_set(self):
        self._step = (2 * math.pi * self._f)/self._sample_rate

    def _post_phase_set(self):
        self._p = (self._p/360) * 2 * math.pi

    def _initialize_osc(self):
        self._i = 0

    def __next__(self):
        value = math.sin(self._i + self._p)
        self._i += self._step
        if self._wave_range != (-1, 1):
            value = self.squish_value(value, *self._wave_range)
        return value * self._a

class SquareOscillator(SineOscillator):
    def __init__(self, frequency=A4, phase=0, amplitude=1, sample_rate=SAMPLING_RATE, wave_range = (-1, 1), threshold=0):
        super().__init__(frequency, phase, amplitude, sample_rate, wave_range)
        self.threshold = threshold

    def __next__(self):
        value = math.sin(self._i + self._p)
        self._i += self._step
        if value < self.threshold:
            value = self._wave_range[0]
        else:
            value = self._wave_range[1]
        return value * self._a

class SawtoothOscillator(Oscillator):
    def _post_freq_set(self):
        self._period = self._sample_rate / self._f

    def _post_phase_set(self):
        self._p = ((self._p + 90)/360) * self._period

    def _initialize_osc(self):
        self._i = 0

    def __next__(self):
        div = (self._i + self._p)/self._period
        value = 2 * (div - math.floor(0.5 + div))
        self._i += 1
        if self._wave_range != (-1, 1):
            value = self.squish_value(value, *self._wave_range)
        return value * self._a

class TriangleOscillator(SawtoothOscillator):
    def __next__(self):
        div = (self._i + self._p)/self._period
        value = 2 * (div - math.floor(0.5 + div))
        value = (abs(value) - 0.5) * 2
        self._i += 1
        if self._wave_range != (-1, 1):
            value = self.squish_value(value, *self._wave_range)
        return value * self._a


class WaveAdder:
    def __init__(self, *oscillators):
        self.oscillators = oscillators
        self.n = len(self.oscillators)

    def __iter__(self):
        [iter(oscillator) for oscillator in self.oscillators]
        return self

    def __next__(self):
        return sum(next(oscillator) for oscillator in self.oscillators)/self.n

# https://askubuntu.com/questions/169400/python-ctypes-and-pulseaudio-segfault-after-upgrade-to-12-04
# https://askubuntu.com/questions/33528/how-do-i-write-raw-bytes-to-a-sound-device

class SampleSpec(ctypes.Structure):
    _fields_ = [("format", ctypes.c_int), ("rate", ctypes.c_int), ("channels", ctypes.c_byte)]

class WavePlayer:
    PA_STREAM_PLAYBACK = 1

    PA_SAMPLE_U8 = 0
    PA_SAMPLE_ALAW = 1
    PA_SAMPLE_ULAW = 2
    PA_SAMPLE_S16LE = 3
    PA_SAMPLE_S16BE = 4
    PA_SAMPLE_FLOAT32LE = 5
    PA_SAMPLE_FLOAT32BE = 6
    PA_SAMPLE_S32LE = 7
    PA_SAMPLE_S32BE = 8
    PA_SAMPLE_S24LE = 9
    PA_SAMPLE_S24BE = 10
    PA_SAMPLE_S24_32LE = 11
    PA_SAMPLE_S24_32BE = 12

    def __init__(self, rate=44100, nchannels=2):
        self.rate = rate
        self.nchannels = nchannels

        self.pa = ctypes.cdll.LoadLibrary("libpulse-simple.so.0")
        self.pa_sample_spec = SampleSpec(self.PA_SAMPLE_FLOAT32LE, rate, nchannels)
        # self.pa_sample_spec = SampleSpec(self.PA_SAMPLE_S16LE, rate, nchannels)
        self.error = ctypes.c_int(0)
        self.s = self.pa.pa_simple_new(None, "Python", self.PA_STREAM_PLAYBACK, None, "Test", ctypes.byref(self.pa_sample_spec), None, None, ctypes.byref(self.error))

    def write(self, data):
        self.pa.pa_simple_write(self.s, data, len(data), 0)

    def __del__(self):
        self.pa.pa_simple_free(self.s)

    def play(self, gen, length):
        nframes = self.rate * self.nchannels * length
        iter(gen)
        if self.nchannels == 2:
            for i in range(nframes):
                value = next(gen)
                packed_value = struct.pack("f", value)
                self.pa.pa_simple_write(self.s, packed_value, len(packed_value), 0)
                self.pa.pa_simple_write(self.s, packed_value, len(packed_value), 0)
        else:
            for i in range(nframes):
                value = next(gen)
                packed_value = struct.pack("f", value)
                self.pa.pa_simple_write(self.s, packed_value, len(packed_value), 0)

    def play(self, gen, length):
        float_size = 4
        nframes = self.rate * self.nchannels * length
        iter(gen)
        buffer = bytearray(nframes * float_size)
        if self.nchannels == 2:
            for i in range(nframes):
                value = next(gen)
                offset = i * float_size
                struct.pack_into("f", buffer, offset, value)
                struct.pack_into("f", buffer, offset, value)
        else:
            for i in range(nframes):
                value = next(gen)
                offset = i * float_size
                struct.pack_into("f", buffer, offset, value)
        buffer = bytes(buffer)
        self.write(buffer)


class WaveWriter:
    # https://soledadpenades.com/posts/2009/fastest-way-to-generate-wav-files-in-python-using-the-wave-module/
    # https://github.com/sole/snippets/blob/master/audio/generate_noise_test_python/script.py
    @staticmethod
    def write(gen, name=None, sample_length=2400, nchannels=2, sampwidth=2, framerate=SAMPLING_RATE, nframes=0, comptype="NONE", compname="not compressed"):
        if not name:
            name = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        if not name.endswith(".wav"):
            name = str(name) + ".wav"
        output = wave.open(str(name), "wb")

        nframes = framerate * sample_length

        output.setparams((nchannels, sampwidth, framerate, nframes, comptype, compname))

        iter(gen)
        # wav = [next(gen) for _ in range(nframes)]

        # buffer = []
        buffer = bytearray()

        if nchannels == 2:
            for i in range(0, sample_length):
                # value = round(wav[i])
                value = round(next(gen))
                packed_value = struct.pack("h", value)
                buffer.extend(packed_value)
                buffer.extend(packed_value)
        else:
            for i in range(0, sample_length):
                # value = round(wav[i])
                value = round(next(gen))
                packed_value = struct.pack("h", value)
                buffer.extend(packed_value)
        output.writeframes(buffer)
        frames = output.getnframes()
        output.close()

def main():
    # A_sine = SineOscillator(amplitude=VOLUME_MAX)
    # WaveWriter.write(A_sine, name="A", sample_length=9600)
    # file = wave.open("A.wav", "rb")
    # print(file.getnframes())
    # file.close()

    A_sine = SineOscillator()

    player = WavePlayer(44100, 2)
    # player.play(A_sine, 10)
    oscillators = list()
    for i in range(45):
        oscillators.append(SineOscillator(frequency=A4*i))
    complex_A = WaveAdder(*oscillators)
    player.play(complex_A, 10)

if __name__ == "__main__":
    main()
