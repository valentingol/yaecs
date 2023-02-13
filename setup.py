"""
Reactive Reality Machine Learning Config System - setup file
Copyright (C) 2022  Reactive Reality

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import pathlib

from setuptools import setup

_dct = {}
with open('yaecs/version.py') as f:
    exec(f.read(), _dct)
VERSION = _dct['__version__']

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
SHORT_README = (HERE / "short-readme.md").read_text()

setup(name='yaecs', version=VERSION,
      description='A Config System designed for experimental purposes',
      long_description=SHORT_README,
      long_description_content_type="text/markdown",
      url='https://gitlab.com/reactivereality/public/yaecs',
      author='Reactive Reality AG', packages=['yaecs', 'yaecs.config'],
      package_dir={'yaecs': 'yaecs', 'yaecs.config': 'yaecs/config'},
      install_requires=["pyyaml==6.0", "mock==4.0.3"])
