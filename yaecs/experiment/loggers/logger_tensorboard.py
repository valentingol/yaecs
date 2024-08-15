""" This file defines the class for the TensorBoard logger. """
import importlib.util
import os
from typing import Any, Optional, Union

from .base_logger import Logger
from .logger_utils import NotImportedModule, value_to_float

try:  # Tensorboard integration, see original package : https://www.tensorflow.org/tensorboard
    import tensorflow
except ImportError:
    tensorflow = NotImportedModule("tensorflow")


class TensorBoardLogger(Logger):
    """ TensorBoard Logger. This logger logs things to a logging directory (logdir). """
    def __init__(self, tracker):
        super().__init__("TensorBoard Logger", tracker)
        self.writers = None
        self.logdir = self.tracker.config.get("logdir", None)

    def check_config_requirements(self) -> str:
        if self.logdir is None:
            return ("Config Requirement Error : no logdir was provided for the tensorboard logger. Provide one using "
                    "the logdir key in the tracker config.")
        return ""

    def check_install(self) -> str:
        if not importlib.util.find_spec("tensorflow"):
            return "Install Error : your experiment tracking config requires tensorflow - currently not installed !"
        return ""

    def get_logger_object(self) -> Any:
        return self.writers

    def start_run(self, experiment_name: str, run_name: str, description: str, params: dict) -> None:
        if "%e" not in self.logdir:
            writer_path = os.path.join(self.logdir, experiment_name, run_name)
        else:
            writer_path = self.logdir.replace("%e", self.tracker.experiment.config.get_experiment_path())
        self.writers = {
            sub_logger: tensorflow.summary.create_file_writer(os.path.join(writer_path, sub_logger))
            for sub_logger in self.tracker.sub_loggers}

    def log_scalar(self, name: str, value: Union[float, int], step: Optional[int] = None,
                   sub_logger: Optional[str] = None, description: Optional[str] = None) -> None:
        value = value_to_float(value, self.name, name)
        if value == "":
            return

        tb_sub_logger = "" if sub_logger is None else sub_logger
        if tb_sub_logger not in self.writers:
            raise ValueError(f"Sub-logger '{tb_sub_logger}' is not defined in the tracker config. You can only use "
                             "tensorboard loggers that have been defined using the 'sub_loggers' key in the tracker "
                             "config.")
        with self.writers[tb_sub_logger].as_default():
            tensorflow.summary.scalar(name=name, data=value, step=0 if step is None else step, description=description)
