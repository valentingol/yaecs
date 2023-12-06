""" This file defines the class for the MLFlow logger. """
import importlib.util
import logging
from typing import Any, Optional, Union

from .base_logger import Logger
from .logger_utils import lazy_import, value_to_float

# MLFlow integration, see original package : https://mlflow.org
mlflow = lazy_import("mlflow")  # pylint: disable=invalid-name

YAECS_LOGGER = logging.getLogger(__name__)


class MLFlowLogger(Logger):
    """ MLFlow Logger. This logger logs things to a MLFlow tracking_uri which can be a server or a folder. """
    def __init__(self, tracker):
        super().__init__("MLFlow Logger", tracker)
        self.run = None
        self.tracking_uri = self.tracker.config.get("tracking_uri", None)

    def check_config_requirements(self) -> str:
        if self.tracking_uri is None:
            return ("Config Requirement Error : no tracking_uri was provided for the mlflow logger. Provide one using "
                    "the tracking_uri key in the tracker config.")
        return ""

    def check_install(self) -> str:
        if not importlib.util.find_spec("mlflow"):
            return "Install Error : your experiment tracking config requires mlflow - currently not installed !"
        return ""

    def get_logger_object(self) -> Any:
        return self.run

    def main_function_context(self):
        return MLFContext()

    def start_run(self, experiment_name: str, run_name: str, description: str, params: dict) -> None:
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(experiment_name)
        self.run = mlflow.start_run(run_name=run_name, description=description)
        mlflow.log_params(params)

    def log_scalar(self, name: str, value: Union[float, int], step: Optional[int] = None,
                   sub_logger: Optional[str] = None, description: Optional[str] = None) -> None:
        self._warn_function_argument("log_scalar", "description", description, None)
        value = value_to_float(value, self.name)
        if value == "":
            return

        extended_name = name
        if sub_logger is not None:
            extended_name = f"{sub_logger}/{extended_name}"
        mlflow.log_metric(key=extended_name, value=value, step=step)


class MLFContext:
    """ Class used to set up the context for mlflow's tracker """

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        mlflow.end_run()
