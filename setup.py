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

VERSION = '1.0.1'

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
SHORT_README = (HERE / "short-readme.md").read_text()

setup(name='yaecs', version=VERSION,
      description='Reactive Reality Machine Learning Config System',
      long_description=SHORT_README,
      long_description_content_type="text/markdown",
      url='https://gitlab.com/reactivereality/public/yaecs',
      author='Reactive Reality AG', packages=['yaecs'],
      package_dir={'yaecs': 'yaecs'}, install_requires=["pyyaml"])
