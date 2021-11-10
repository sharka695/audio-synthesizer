import math
import itertools

SAMPLING_RATE = 44100

A4 = 440


def sin_osc_generator(frequency, amplitude=1, phase=0, sample_rate=SAMPLING_RATE):
    phase = (phase/360) * 2 * math.pi
    incr = (2* math.pi * frequency) / sample_rate
    return (math.sin(phase + step) * amplitude for step in itertools.count(start=0, step=incr))

osc = sin_osc_generator(A4, SAMPLING_RATE)
samples = [next(osc) for _ in range(SAMPLING_RATE)]
print(samples)
