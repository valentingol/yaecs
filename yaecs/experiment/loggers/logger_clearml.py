""" This file defines the class for the ClearML logger. """
import importlib.util
import logging
import os
from typing import Any, Optional, Union
import warnings

from .base_logger import Logger
from .logger_utils import lazy_import, value_to_float
from ..experiment_utils import format_mode

# ClearML integration, see original package : https://clear.ml
clearml = lazy_import("clearml")  # pylint: disable=invalid-name

YAECS_LOGGER = logging.getLogger(__name__)


class ClearMLLogger(Logger):
    """ ClearML Logger. This logger logs things to a ClearML server setup in a clearml.conf config. """
    def __init__(self, tracker):
        super().__init__("ClearML Logger", tracker)
        self.task = None
        self.project_name = self.tracker.config.get("project_name", None)

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
                                      continue_last_task=bool(os.getenv("PICKUP")))
        self.task.set_comment(description)
        self.task.connect(params)

    def log_scalar(self, name: str, value: Union[float, int], step: Optional[int] = None,
                   sub_logger: Optional[str] = None, description: Optional[str] = None) -> None:
        value = value_to_float(value, self.name)
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
        if description is not None:
            YAECS_LOGGER.warning("WARNING : in log_scalar : 'description' is not used in clearml.")

    def log_image(self, name: str, image, step: Optional[int] = None, sub_logger: Optional[str] = None) -> None:
        # Support for matplotlib figures logging, see original package : https://matplotlib.org/
        matplotlib = lazy_import("matplotlib")  # pylint: disable=invalid-name
        # Support to save numpy arrays as images, see original package : https://numpy.org/
        np = lazy_import("numpy")  # pylint: disable=invalid-name
        # Support to save numpy arrays as images, see original package : https://pypi.org/project/Pillow/
        Image = lazy_import("PIL.Image")  # pylint: disable=invalid-name
        # Support for plotly figures, see original package : https://plotly.com/python/
        plotly = lazy_import("plotly")  # pylint: disable=invalid-name
        sub_logger = "" if sub_logger is None else sub_logger

        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=UserWarning)
            if isinstance(image, str):
                self.task.logger.report_image(title=name, series=sub_logger, local_path=image, iteration=step)
            elif isinstance(image, np.ndarray):
                self.task.logger.report_image(title=name, series=sub_logger, image=image.astype(np.uint8),
                                              iteration=step)
            elif isinstance(image, Image):
                self.task.logger.report_image(title=name, series=sub_logger, image=np.array(image, dtype=np.uint8),
                                              iteration=step)
            elif isinstance(image, matplotlib.figure.Figure):
                self.task.logger.report_matplotlib(title=name, series=sub_logger, iteration=step, figure=image)
            elif isinstance(image, plotly.graph_objects.Figure):
                self.task.logger.report_plotly(title=name, series=sub_logger, iteration=step, figure=image)
            else:
                self.task.logger.report_image(title=name, series=sub_logger, image=np.array(image, dtype=np.uint8),
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
