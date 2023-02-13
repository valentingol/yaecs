"""
Reactive Reality Machine Learning Config System - Configuration object
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
import importlib.util
from typing import Any, Union

from .user_utils import tqdm_file

try:
    _NEW = True
    import pytorch_lightning.callbacks.progress.tqdm_progress.TQDMProgressBar as ProgressBar
except ImportError:
    _NEW = False
    from pytorch_lightning.callbacks.progress import ProgressBar
if importlib.util.find_spec("ipywidgets") is not None:
    from tqdm.auto import tqdm as _tqdm  # pylint: disable=import-error
else:
    from tqdm import tqdm as _tqdm  # pylint: disable=import-error


_PAD_SIZE = 5


class Tqdm(_tqdm):
    """ Re-implements pytorch-lightning's TQDM loading bars to make them more YAECS-friendly. """

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # pylint: disable=useless-super-delegation
        """Custom tqdm progressbar where we append 0 to floating points/strings to prevent the progress bar from
        flickering."""
        # this just to make the make docs happy, otherwise it pulls docs which has some issues...
        super().__init__(*args, **kwargs)

    @staticmethod
    def format_num(n: Union[int, float, str]) -> str:
        """Add additional padding to the formatted numbers."""
        should_be_padded = isinstance(n, (float, str))
        if not isinstance(n, str):
            n = _tqdm.format_num(n)
            assert isinstance(n, str)
        if should_be_padded and "e" not in n:
            if "." not in n and len(n) < _PAD_SIZE:
                try:
                    _ = float(n)
                except ValueError:
                    return n
                n += "."
            n += "0" * (_PAD_SIZE - len(n))
        return n


class TrackerFriendlyBar(ProgressBar):
    """
    Progress bar class to use instead of TQDMProgressBar (formerly ProgressBar) in pytorch-lightning when yaecs is used
    as a tracker.
    Usage : https://pytorch-lightning.readthedocs.io/en/stable/common/progress_bar.html
    """
    def init_sanity_tqdm(self) -> Tqdm:
        """Override this to customize the tqdm bar for the validation sanity run."""
        tqdm_bar = Tqdm(
            desc=self.sanity_check_description if _NEW else "Validation sanity check",
            position=(2 * self.process_position),
            disable=self.is_disabled,
            leave=False,
            dynamic_ncols=True,
            file=tqdm_file(),
        )
        return tqdm_bar

    def init_train_tqdm(self) -> Tqdm:
        """Override this to customize the tqdm bar for training."""
        tqdm_bar = Tqdm(
            desc=self.train_description if _NEW else "Training",
            initial=self.train_batch_idx,
            position=(2 * self.process_position),
            disable=self.is_disabled,
            leave=True,
            dynamic_ncols=True,
            file=tqdm_file(),
            smoothing=0,
        )
        return tqdm_bar

    def init_predict_tqdm(self) -> Tqdm:
        """Override this to customize the tqdm bar for predicting."""
        tqdm_bar = Tqdm(
            desc=self.predict_description if _NEW else "Predicting",
            initial=self.train_batch_idx,
            position=(2 * self.process_position),
            disable=self.is_disabled,
            leave=True,
            dynamic_ncols=True,
            file=tqdm_file(),
            smoothing=0,
        )
        return tqdm_bar

    def init_validation_tqdm(self) -> Tqdm:
        """Override this to customize the tqdm bar for validation."""
        # The main progress bar doesn't exist in `trainer.validate()`
        has_main_bar = self.trainer.state.fn != "validate" if _NEW else self.main_progress_bar is not None
        tqdm_bar = Tqdm(
            desc=self.validation_description if _NEW else "Validating",
            position=(2 * self.process_position + has_main_bar),
            disable=self.is_disabled,
            leave=(not has_main_bar) and _NEW,
            dynamic_ncols=True,
            file=tqdm_file(),
        )
        return tqdm_bar

    def init_test_tqdm(self) -> Tqdm:
        """Override this to customize the tqdm bar for testing."""
        tqdm_bar = Tqdm(
            desc="Testing",
            position=(2 * self.process_position),
            disable=self.is_disabled,
            leave=True,
            dynamic_ncols=True,
            file=tqdm_file(),
        )
        return tqdm_bar
