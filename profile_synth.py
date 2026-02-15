#!/usr/bin/env python3
"""Profile the VOOG synth audio rendering to find performance bottlenecks."""

import cProfile
import pstats
import io
import time
import numpy as np

from synth.config import SAMPLE_RATE, BUFFER_SIZE
from synth.engine.channel import Channel
from synth.patch.default_patches import DEFAULT_PATCHES


def run_benchmark(seconds: float = 5.0, num_voices: int = 6, patch_name: str = "Bass Voog"):
    """Render audio offline to measure pure DSP performance."""
    channel = Channel(0)

    # Load a demanding preset
    patch = DEFAULT_PATCHES.get(patch_name, list(DEFAULT_PATCHES.values())[1])
    channel.set_patch(patch)
    print(f"Patch: {patch.name}")
    print(f"Voices: {num_voices}, Buffer: {BUFFER_SIZE}, Rate: {SAMPLE_RATE}")
    print(f"Rendering {seconds}s of audio...\n")

    # Trigger multiple notes (a chord) to simulate real polyphony
    notes = [48, 52, 55, 60, 64, 67, 72, 76][:num_voices]
    for note in notes:
        channel.note_on(note, 100)

    total_samples = int(SAMPLE_RATE * seconds)
    num_buffers = total_samples // BUFFER_SIZE

    # Warm up (1 buffer)
    channel.render(BUFFER_SIZE)

    # Timed run
    t0 = time.perf_counter()
    for _ in range(num_buffers):
        channel.render(BUFFER_SIZE)
    elapsed = time.perf_counter() - t0

    audio_duration = num_buffers * BUFFER_SIZE / SAMPLE_RATE
    cpu_ratio = elapsed / audio_duration
    print(f"--- Timing ---")
    print(f"Audio duration: {audio_duration:.2f}s")
    print(f"Render time:    {elapsed:.3f}s")
    print(f"CPU ratio:      {cpu_ratio:.2f}x realtime")
    if cpu_ratio >= 1.0:
        print(f"  ** CANNOT keep up with realtime! Need {cpu_ratio:.1f}x speedup **")
    else:
        print(f"  Headroom: {(1.0 - cpu_ratio) * 100:.0f}%")
    print()


def run_profile(seconds: float = 3.0, num_voices: int = 6, patch_name: str = "Bass Voog"):
    """Profile the render path with cProfile."""
    channel = Channel(0)

    patch = DEFAULT_PATCHES.get(patch_name, list(DEFAULT_PATCHES.values())[1])
    channel.set_patch(patch)

    notes = [48, 52, 55, 60, 64, 67, 72, 76][:num_voices]
    for note in notes:
        channel.note_on(note, 100)

    total_samples = int(SAMPLE_RATE * seconds)
    num_buffers = total_samples // BUFFER_SIZE

    # Warm up
    channel.render(BUFFER_SIZE)

    pr = cProfile.Profile()
    pr.enable()
    for _ in range(num_buffers):
        channel.render(BUFFER_SIZE)
    pr.disable()

    # Print sorted by cumulative time
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(30)
    print("--- cProfile (top 30 by cumulative time) ---")
    print(s.getvalue())

    # Also print by tottime (self time)
    s2 = io.StringIO()
    ps2 = pstats.Stats(pr, stream=s2).sort_stats("tottime")
    ps2.print_stats(30)
    print("--- cProfile (top 30 by self time) ---")
    print(s2.getvalue())


if __name__ == "__main__":
    print("=" * 60)
    print("VOOG Synth Performance Profile")
    print("=" * 60)
    print()

    # First: quick timing benchmark
    run_benchmark(seconds=5.0, num_voices=6)

    # Then: detailed cProfile
    run_profile(seconds=3.0, num_voices=6)
