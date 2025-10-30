""" This file defines the class for the ClearML logger. """
import importlib.util
import logging
import os
from typing import Any, Optional, Union

from .base_logger import Logger
from .logger_utils import NotImportedModule, value_to_float
from ..experiment_utils import format_mode

try:  # ClearML integration, see original package : https://clear.ml
    import clearml
except ImportError:
    clearml = NotImportedModule("clearml")
try:  # Support for matplotlib figures logging, see original package : https://matplotlib.org/
    import matplotlib
except ImportError:
    matplotlib = NotImportedModule("matplotlib")
try:  # Support to save numpy arrays as images, see original package : https://numpy.org/
    import numpy as np
except ImportError:
    np = NotImportedModule("numpy")
try:  # Support to save numpy arrays as images, see original package : https://pypi.org/project/Pillow/
    from PIL import Image
except ImportError:
    Image = NotImportedModule("PIL")
try:  # Support for plotly figures, see original package : https://plotly.com/python/
    import plotly
except ImportError:
    plotly = NotImportedModule("plotly")

YAECS_LOGGER = logging.getLogger(__name__)


class ClearMLLogger(Logger):
    """
    ClearML Logger. This logger logs things to a ClearML server setup in a clearml.conf config.
    Attributes list:
        - project_name : str : name of the ClearML project where to log experiments.
        - task_kwargs : dict : additional keyword arguments to pass to clearml.Task.init().
    """

    def __init__(self, tracker):
        super().__init__("ClearML Logger", tracker)
        self.possible_attributes = ["project_name", "task_kwargs"]
        self.task = None
        self.project_name = self.tracker.config.get("project_name", None)
        self.task_kwargs = self.tracker.config.get("task_kwargs", {})

    def check_config_requirements(self) -> str:
        if self.project_name is None:
            return ("Config Requirement Error : no project name was provided for the clearml logger. Provide one using "
                    "the project_name key in the tracker config.")
        return ""

    def check_install(self) -> str:
        error = ""
        if not os.path.isfile(os.path.expanduser("~/clearml.conf")):
            error = ("Install Error : no 'clearml.conf' file detected in your home directory. Please run 'clearml-init'"
                     " as explained in https://clear.ml/docs/latest/docs/getting_started/ds/ds_first_steps.")
        if not importlib.util.find_spec("clearml"):
            error += "\n" if error else ""
            error += "Install Error : your experiment tracking config requires clearml - currently not installed !"
        return error

    def get_logger_object(self) -> Any:
        return self.task

    def main_function_context(self):
        return CMLContext(self.tracker)

    def start_run(self, experiment_name: str, run_name: str, description: str, params: dict) -> None:
        self.task = clearml.Task.init(project_name=self.project_name,
                                      task_name=f"{experiment_name}/{run_name}",
                                      task_type=self._get_tast_type(),
                                      continue_last_task=bool(os.getenv("PICKUP")),
                                      **self.task_kwargs)
        self.task.set_comment(description)
        self.task.connect(params)

    def log_scalar(self, name: str, value: Union[float, int], step: Optional[int] = None,
                   sub_logger: Optional[str] = None, description: Optional[str] = None) -> None:
        self._warn_function_argument("log_scalar", "description", description, None)
        value = value_to_float(value, self.name, name)
        if value == "":
            return

        if step is None:
            self.task.logger.report_single_value(name=name, value=value)
        else:
            if sub_logger is None:
                names_hierarchy = name.split("/")
                if len(names_hierarchy) > 1:
                    title = "/".join(names_hierarchy[:-1])
                else:
                    title = names_hierarchy[-1]
                series = names_hierarchy[-1]
            else:
                title = name
                series = sub_logger
            self.task.logger.report_scalar(title=title, series=series, value=value, iteration=step)

    def log_image(self, name: str, image: Any, step: Optional[int] = None, sub_logger: Optional[str] = None,
                  extension: str = "png") -> None:
        self._warn_function_argument("log_image", "extension", extension, "png")
        sub_logger = "logged_images" if sub_logger is None else sub_logger

        if isinstance(image, str):
            self.task.logger.report_image(title=sub_logger, series=name, local_path=image, iteration=step)
        elif isinstance(image, np.ndarray):
            self.task.logger.report_image(title=sub_logger, series=name, image=image.astype(np.uint8),
                                          iteration=step)
        elif isinstance(image, Image.Image):
            self.task.logger.report_image(title=sub_logger, series=name, image=np.array(image, dtype=np.uint8),
                                          iteration=step)
        elif isinstance(image, matplotlib.figure.Figure):
            self.task.logger.report_matplotlib_figure(title=sub_logger, series=name, iteration=step, figure=image)
        elif isinstance(image, plotly.graph_objects.Figure):
            self.task.logger.report_plotly(title=sub_logger, series=name, iteration=step, figure=image)
        else:
            self.task.logger.report_image(title=sub_logger, series=name, image=np.array(image, dtype=np.uint8),
                                          iteration=step)

    def _get_tast_type(self):
        """ Returns the task type for the ClearML task, inferred from the experiment mode if there is one. """
        task_types = {
            "TRAINING": clearml.Task.TaskTypes.training,
            "TESTING": clearml.Task.TaskTypes.testing,
            "VALIDATION": clearml.Task.TaskTypes.testing,
            "INFERENCE": clearml.Task.TaskTypes.inference,
            "DATA PROCESSING": clearml.Task.TaskTypes.data_processing,
            "DEBUG": clearml.Task.TaskTypes.training,
        }
        mode_param = self.tracker.experiment.config.get_hook("mode")
        mode = format_mode(self.tracker.experiment.config[mode_param[0]]) if mode_param else "TRAINING"
        task_type = clearml.Task.TaskTypes.custom
        for key, value in task_types.items():
            if key in mode:
                task_type = value
                break
        return task_type


class CMLContext:
    """ Class used to set up the context for ClearML's tracker """

    def __init__(self, tracker):
        """
        Initialises a context used to close the ClearML runs when they are done.

        :param tracker: tracker object where to find the ClearML runs
        """
        self.tracker = tracker

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tracker.loggers["clearml"].close()
