#!/usr/bin/env python3
from setuptools import setup
from setuptools_rust import RustExtension

# TODO: Is there any way I can get setup.py to install setuptools_rust?
# https://github.com/fafhrd91/setuptools-rust

setup(name='game-launcher',
      # TODO: Unify this version definition with the source
      version='0.0a0',
      url='https://github.com/ssokolow/game_launcher',
      author='Stephan Sokolow',
      rust_extensions=[RustExtension('src.core', 'game_launcher_core/Cargo.toml')],
      packages=['src'],
      # rust extensions are not zip safe, just like C-extensions.
      zip_safe=False
)
