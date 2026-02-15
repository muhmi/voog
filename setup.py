from setuptools import setup, Extension
import numpy as np

moog_filter_ext = Extension(
    "synth.dsp._moog_filter_c",
    sources=["synth/dsp/_moog_filter_c.c"],
    include_dirs=[np.get_include()],
)

setup(
    name="voog",
    version="0.1.0",
    packages=["synth", "synth.dsp", "synth.engine", "synth.gui", "synth.midi", "synth.patch", "synth.cli"],
    ext_modules=[moog_filter_ext],
    install_requires=["numpy", "sounddevice"],
)
