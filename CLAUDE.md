# CLAUDE.md - Technical Reference

Python/tkinter Moog-style polyphonic synthesizer with C extension DSP and Nuitka packaging.

## Build Commands

```bash
make run              # Launch synth GUI
make build-ext        # Compile C extension (Moog filter)
make profile          # Run performance profiler (5s, 6 voices)
make distribute       # Build standalone binary with Nuitka (LTO)
make distribute-fast  # Build standalone binary (no LTO, faster)
make fix-tcl-perms    # Fix Homebrew Tcl/Tk permissions for Nuitka
make clean            # Remove dist/, build/, *.so, __pycache__
```

## Architecture

```
AudioEngine (sounddevice callback, 256-sample blocks)
 └── Channel[] (4 channels, each with VoiceAllocator)
      └── Voice[] (up to 8 per channel)
           ├── Oscillator[3]    # Wavetable (sine/saw/square/tri), 2048 samples
           ├── NoiseGenerator   # White/pink noise
           ├── MoogFilter       # 24dB/oct Huovilainen ladder
           ├── Envelope (amp)   # ADSR, control-rate with audio-rate interpolation
           ├── Envelope (filter)
           ├── LFO              # Modulates filter/pitch/amp
           └── Glide            # Portamento (off/always/legato)
```

## DSP Constants

```python
SAMPLE_RATE = 44100
BUFFER_SIZE = 256          # ~5.8ms per callback
MAX_VOICES = 8             # Per channel
NUM_CHANNELS = 4
NUM_OSCILLATORS = 3
WAVETABLE_SIZE = 2048
CONTROL_RATE_DIVIDER = 16  # Envelope/LFO update every 16 samples
```

## Filter Backend Priority

The Moog filter has three backends, selected at import time:

1. **C extension** (`synth/dsp/_moog_filter_c.c`) — compiled via `setup.py`, fastest
2. **Numba JIT** — `pip install numba`, ~150MB, near-C speed
3. **Pure Python** — no deps, significantly slower

Check active backend: `from synth.dsp.filter import _FILTER_BACKEND`

## C Extension

```bash
python setup.py build_ext --inplace   # Builds synth/dsp/_moog_filter_c.*.so
```

Single-file CPython extension using NumPy C API. Implements `moog_ladder_process()` — the Huovilainen Moog ladder filter (24dB/oct, 4 cascaded one-pole stages with feedback).

## Nuitka Packaging

Builds a standalone onefile binary (`dist/voog`, ~14MB with zstandard compression).

Key flags:
- `--python-flag=-m` + `synth` directory — required for relative imports in `__main__.py`
- `--nofollow-import-to=numba,llvmlite` — saves ~300 C files, not needed with C extension
- `--enable-plugin=tk-inter` — bundles Tcl/Tk data files

**macOS Homebrew issue:** Tcl/Tk files ship as `-r--r--r--`. Nuitka copies them preserving permissions, then `xattr -cr` fails. Fix: `make fix-tcl-perms` before building (runs `chmod -R u+w` on source Tcl/Tk dirs).

## Key Files

| File | Purpose |
|------|---------|
| `synth/__main__.py` | Entry point (--gui, --patch, --midi-port) |
| `synth/config.py` | Global constants (sample rate, buffer size) |
| `synth/dsp/filter.py` | Moog filter with 3-tier backend fallback |
| `synth/dsp/_moog_filter_c.c` | C extension for Moog filter |
| `synth/dsp/oscillator.py` | Wavetable oscillator with vectorized phase |
| `synth/dsp/envelope.py` | ADSR with vectorized interpolation |
| `synth/engine/voice.py` | Voice render pipeline |
| `synth/engine/audio_engine.py` | sounddevice callback + MIDI queue |
| `synth/patch/default_patches.py` | 19 factory presets |
| `setup.py` | C extension build config |
| `nuitka-project.toml` | Nuitka build config |
| `profile_synth.py` | Offline profiling (renders 5s, 6 voices) |

## Performance Notes

Profiled on M2 Mac, 5s render, 6 voices (Bass Voog patch):

| Config | CPU ratio | Headroom |
|--------|-----------|----------|
| Original | 0.66x | 34% |
| + vectorized osc/env | 0.52x | 48% |
| + C extension filter | 0.14x | 86% |

The filter is the #1 bottleneck (~50% of render time without C ext or Numba).
Oscillator and envelope were vectorized with numpy (cumsum, arange) to eliminate per-sample Python loops.

## Branches

- `main` — synced with upstream (gpasquero/voog)
- `perf/audio-engine-optimization` — oscillator/envelope vectorization (PR candidate)
- `dev/nuitka-packaging` — C extension + Nuitka onefile build + CI
