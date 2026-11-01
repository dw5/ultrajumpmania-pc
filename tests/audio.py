#!/usr/bin/env python3
# Compares two raw stereo s16 recordings: loudness, long-term spectrum and beat tempo.
import sys

import numpy as np


def load(path):
    d = np.frombuffer(open(path, 'rb').read(), dtype='<i2')
    return d[:len(d) // 2 * 2].reshape(-1, 2).astype(float) / 32768


def spectrum(x, rate):
    n = 8192
    w = np.hanning(n)
    m = x.mean(axis=1)
    p = sum(np.abs(np.fft.rfft(m[i:i + n] * w)) ** 2 for i in range(0, len(m) - n, n // 2))
    f = np.fft.rfftfreq(n, 1 / rate)
    edges = np.geomspace(60, min(rate / 2, 12000), 25)
    return np.array([p[(f >= a) & (f < b)].sum() + 1e-12 for a, b in zip(edges, edges[1:])])


def tempo(x, rate):
    hop = rate // 100
    m = np.abs(x.mean(axis=1))
    env = np.array([m[i:i + hop].mean() for i in range(0, len(m) - hop, hop)])
    d = np.maximum(np.diff(env), 0)
    d -= d.mean()
    ac = np.correlate(d, d, 'full')[len(d):]
    lo, hi = 30, 200
    lag = lo + int(np.argmax(ac[lo:hi]))
    return 6000 / lag


def envelope(x, rate):
    hop = rate // 100
    m = np.abs(x.mean(axis=1))
    e = np.array([m[i:i + hop].mean() for i in range(0, len(m) - hop, hop)])
    d = np.maximum(np.diff(e), 0)
    return (d - d.mean()) / (d.std() + 1e-9)


def match(a, b):
    # Best alignment of the two envelopes, at the same speed and slightly stretched.
    best = {}
    for stretch in (0.97, 0.98, 0.99, 1.0, 1.01, 1.02, 1.03):
        n = int(len(b) * stretch)
        s = np.interp(np.arange(n) / stretch, np.arange(len(b)), b)
        size = len(a) + len(s)
        c = np.fft.irfft(np.fft.rfft(a, size) * np.conj(np.fft.rfft(s, size)), size)
        best[stretch] = float(c.max() / min(len(a), len(s)))
    return best


for rate_e, rate_p in ((44100, 32000),):
    e, p = load(sys.argv[1]), load(sys.argv[2])
    print('seconds', round(len(e) / rate_e, 1), round(len(p) / rate_p, 1), 'assuming rates', rate_e, rate_p)
    print('rms', round(float(np.sqrt((e ** 2).mean())), 4), round(float(np.sqrt((p ** 2).mean())), 4), 'peak', round(float(np.abs(e).max()), 3), round(float(np.abs(p).max()), 3))
    a, b = spectrum(e, rate_e), spectrum(p, rate_p)
    a, b = a / a.sum(), b / b.sum()
    da, db = 10 * np.log10(a), 10 * np.log10(b)
    print('spectrum correlation', round(float(np.corrcoef(da, db)[0, 1]), 3), 'largest band difference dB', round(float(np.abs(da - db).max()), 1))
    print('bands dB (emu-port)', [round(float(x)) for x in da - db])
    print('stereo width', round(float(np.abs(e[:, 0] - e[:, 1]).mean()), 4), round(float(np.abs(p[:, 0] - p[:, 1]).mean()), 4))
    print('beat match by speed', {k: round(v, 2) for k, v in match(envelope(e, rate_e), envelope(p, rate_p)).items()})
