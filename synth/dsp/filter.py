import numpy as np

from ..config import SAMPLE_RATE

# Filter implementation priority: C extension > Numba JIT > pure Python
_FILTER_BACKEND = "python"

try:
    from ._moog_filter_c import moog_ladder_process as _moog_ladder_process
    _FILTER_BACKEND = "c"
except ImportError:
    try:
        import numba
        _HAS_NUMBA = True
    except ImportError:
        _HAS_NUMBA = False

    if _HAS_NUMBA:
        @numba.jit(nopython=True, cache=True)
        def _moog_ladder_process(samples, cutoff_buf, resonance, state, sr):
            """Huovilainen Moog ladder filter – 24dB/oct, Numba JIT."""
            n = len(samples)
            out = np.empty(n, dtype=np.float64)
            s0, s1, s2, s3 = state[0], state[1], state[2], state[3]
            for i in range(n):
                fc = cutoff_buf[i]
                f = 2.0 * sr * np.tan(np.pi * fc / sr) if fc < sr * 0.49 else sr * 0.49 * 2.0
                g = f / (2.0 * sr)
                G = g / (1.0 + g)
                r = resonance * 4.0
                S = G * G * G * s0 + G * G * s1 + G * s2 + s3
                u = (samples[i] - r * S) / (1.0 + r * G * G * G * G)
                v = (u - s0) * G
                lp = v + s0
                s0 = lp + v
                v = (lp - s1) * G
                lp = v + s1
                s1 = lp + v
                v = (lp - s2) * G
                lp = v + s2
                s2 = lp + v
                v = (lp - s3) * G
                lp = v + s3
                s3 = lp + v
                out[i] = lp
            state[0], state[1], state[2], state[3] = s0, s1, s2, s3
            return out
        _FILTER_BACKEND = "numba"
    else:
        def _moog_ladder_process(samples, cutoff_buf, resonance, state, sr):
            """Pure-Python fallback (slower)."""
            n = len(samples)
            out = np.empty(n, dtype=np.float64)
            s0, s1, s2, s3 = state[0], state[1], state[2], state[3]
            for i in range(n):
                fc = cutoff_buf[i]
                fc = min(fc, sr * 0.49)
                f = 2.0 * sr * np.tan(np.pi * fc / sr)
                g = f / (2.0 * sr)
                G = g / (1.0 + g)
                r = resonance * 4.0
                S = G * G * G * s0 + G * G * s1 + G * s2 + s3
                u = (samples[i] - r * S) / (1.0 + r * G * G * G * G)
                v = (u - s0) * G
                lp = v + s0
                s0 = lp + v
                v = (lp - s1) * G
                lp = v + s1
                s1 = lp + v
                v = (lp - s2) * G
                lp = v + s2
                s2 = lp + v
                v = (lp - s3) * G
                lp = v + s3
                s3 = lp + v
                out[i] = lp
            state[0], state[1], state[2], state[3] = s0, s1, s2, s3
            return out


class MoogFilter:
    def __init__(self):
        self.cutoff = 8000.0      # Hz
        self.resonance = 0.0      # 0..1
        self.env_amount = 0.0     # semitones of cutoff modulation
        self.key_tracking = 0.0   # 0..1, 1 = full tracking
        self._state = np.zeros(4, dtype=np.float64)

    def render(self, samples: np.ndarray, cutoff_mod: np.ndarray | None = None) -> np.ndarray:
        """Process audio through the Moog ladder filter.

        cutoff_mod: optional per-sample modulation in Hz added to base cutoff.
        """
        n = len(samples)
        if cutoff_mod is not None:
            cutoff_buf = np.clip(self.cutoff + cutoff_mod, 20.0, SAMPLE_RATE * 0.49)
        else:
            cutoff_buf = np.full(n, min(self.cutoff, SAMPLE_RATE * 0.49), dtype=np.float64)

        return _moog_ladder_process(
            samples.astype(np.float64),
            cutoff_buf.astype(np.float64),
            self.resonance,
            self._state,
            float(SAMPLE_RATE),
        )

    def reset(self):
        self._state[:] = 0.0
