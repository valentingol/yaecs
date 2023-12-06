""" This file defines the class for the Sacred logger. """
from functools import partial
import importlib.util
import logging
from typing import Any, Optional, Union

from .base_logger import Logger
from .logger_utils import lazy_import, value_to_float

# Sacred integration, see original package : https://sacred.readthedocs.io/
sacred = lazy_import("sacred")  # pylint: disable=invalid-name

YAECS_LOGGER = logging.getLogger(__name__)


class SacredLogger(Logger):
    """ Sacred Logger. This logger logs things to a setup database. """
    def __init__(self, tracker):
        super().__init__("Sacred Logger", tracker)
        self.experiment = None
        self.db_name = self.tracker.config.get("db_name", None)
        self.db_url = self.tracker.config.get("db_url", None)
        self.description: Optional[str] = None

    def check_config_requirements(self) -> str:
        errors = ""
        if self.db_name is None:
            errors += ("Config Requirement Error : no db_name was provided for the sacred logger. Provide one "
                       "using the db_name key in the tracker config.")
        if self.db_url is None:
            errors += "\n" if errors else ""
            errors += ("Config Requirement Error : no db_url was provided for the sacred logger. Provide one "
                       "using the db_url key in the tracker config.")
        return errors

    def check_install(self) -> str:
        if not importlib.util.find_spec("sacred"):
            return "Install Error : your experiment tracking config requires sacred - currently not installed !"
        return ""

    def modify_main_function(self, main_function):
        self.experiment.main(main_function)
        main_function = partial(self.experiment.run, meta_info={"comment": self.description})
        main_function.__name__ = self.tracker.experiment.main_function.__name__  # partial functions do not have names
        return main_function

    def get_logger_object(self) -> Any:
        return self.experiment

    def start_run(self, experiment_name: str, run_name: str, description: str, params: dict) -> None:
        self.experiment = sacred.Experiment(f"{experiment_name}/{run_name}")
        self.experiment.observers.append(sacred.observers.MongoObserver(url=self.db_url, db_name=self.db_name))
        self.experiment.add_config(params)
        self.description = description

    def log_scalar(self, name: str, value: Union[float, int], step: Optional[int] = None,
                   sub_logger: Optional[str] = None, description: Optional[str] = None) -> None:
        self._warn_function_argument("log_scalar", "description", description, None)
        value = value_to_float(value, self.name)
        if value == "":
            return

        extended_name = name
        if sub_logger is not None:
            extended_name = f"{sub_logger}/{extended_name}"
        self.experiment.log_scalar(name=extended_name, value=value, step=step)
