"""
Reactive Reality Machine Learning Config System
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
import logging
import sys

# Logging configuration code is reused from the __init__.py in pytorch-lightning.
# See : https://github.com/Lightning-AI/lightning/blob/master/src/pytorch_lightning/__init__.py
_ROOT_LOGGER = logging.root
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)

# if root logger has handlers, propagate messages up and let root logger process them
if not _ROOT_LOGGER.hasHandlers():
    _HANDLER = logging.StreamHandler(sys.stdout)
    _HANDLER.setFormatter(logging.Formatter(fmt="[CONFIG] %(message)s"))
    _LOGGER.addHandler(_HANDLER)
    _LOGGER.propagate = False

from .config.config import Configuration  # pylint: disable=wrong-import-position # noqa: E402
from .config_history import ConfigHistory  # pylint: disable=wrong-import-position # noqa: E402
from .experiment.experiment import Experiment  # pylint: disable=wrong-import-position # noqa: E402
from .user_utils import (  # pylint: disable=wrong-import-position # noqa: E402
    get_template_class,
    make_config,
    tqdm_file,
)
from .yaecs_utils import (  # pylint: disable=wrong-import-position # noqa: E402
    assign_order,
    assign_yaml_tag,
    hook,
    Priority,
)

try:
    from ._version import version as __version__
    from ._version import version_tuple
except ImportError:
    __version__ = "unknown version"
    version_tuple = (0, 0, "unknown_version")

__all__ = ['__version__', 'assign_order', 'assign_yaml_tag', 'ConfigHistory', 'Configuration', 'Experiment',
           'get_template_class', 'hook', 'make_config', 'Priority', 'tqdm_file', 'version_tuple']
