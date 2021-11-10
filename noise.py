# https://askubuntu.com/questions/169400/python-ctypes-and-pulseaudio-segfault-after-upgrade-to-12-04

# https://askubuntu.com/questions/33528/how-do-i-write-raw-bytes-to-a-sound-device

import ctypes
import struct
import random

class SampleSpec(ctypes.Structure):
    _fields_ = [("format", ctypes.c_int), ("rate", ctypes.c_int), ("channels", ctypes.c_byte)]

class NoiseMaker (object):
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

    def __init__(self, rate, channels):
        self.pa = ctypes.cdll.LoadLibrary("libpulse-simple.so.0")
        self.pa_sample_spec = SampleSpec(self.PA_SAMPLE_U8, 44100, 2)
        self.error = ctypes.c_int(0)
        self.s = self.pa.pa_simple_new(None, "Python", self.PA_STREAM_PLAYBACK, None, "Test", ctypes.byref(self.pa_sample_spec), None, None, ctypes.byref(self.error))


    def write(self, data):
        self.pa.pa_simple_write(self.s, data, len(data), 0)

    def __del__(self):
        self.pa.pa_simple_free(self.s)


one_second_noise = bytes(random.randint(0, 255) for i in range(44100*2))
NoiseMaker(44100, 2).write(one_second_noise)
