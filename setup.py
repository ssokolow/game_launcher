#!/usr/bin/env python3
from setuptools import setup

# Workaround for https://github.com/PyO3/setuptools-rust/issues/2
try:
    from setuptools_rust import RustExtension, Binding
except ImportError:
    import subprocess
    import sys
    errno = subprocess.call([sys.executable, '-m', 'pip', 'install', 'setuptools-rust'])
    if errno:
        print("Please install setuptools-rust package")
        raise SystemExit(errno)
    else:
        from setuptools_rust import RustExtension

setup(name='game-launcher',
      # TODO: Unify this version definition with the source
      version='0.0a0',
      url='https://github.com/ssokolow/game_launcher',
      author='Stephan Sokolow',
      rust_extensions=[RustExtension('src.core',
                                     'game_launcher_core/Cargo.toml',
                                     binding=Binding.RustCPython)],
      packages=['src'],
      # rust extensions are not zip safe, just like C-extensions.
      zip_safe=False
)
