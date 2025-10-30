""" This module defines the AggregateLogger class. """
import os
import logging
from typing import Any, Dict, List, Optional, Union

from .base_logger import Logger
from .logger_basic import BasicLogger
from .logger_clearml import ClearMLLogger
from .logger_mlflow import MLFlowLogger
from .logger_sacred import SacredLogger
from .logger_tensorboard import TensorBoardLogger

LOGGERS = {
    "basic": BasicLogger,
    "clearml": ClearMLLogger,
    "mlflow": MLFlowLogger,
    "sacred": SacredLogger,
    "tensorboard": TensorBoardLogger,
}
YAECS_LOGGER = logging.getLogger(__name__)


class AggregateLogger:
    """ This class defines an aggregation of different loggers and functions that use aggregated loggers. """
    def __init__(self, tracker, logger_list):
        self.tracker = tracker
        if any(name not in LOGGERS for name in logger_list):
            absent = [name for name in logger_list if name not in LOGGERS]
            raise ValueError(f"Unknown logger(s) {absent}. Available loggers are {list(LOGGERS.keys())}.")
        # Do not track if in a pytorch-lightning spawned process.
        self.types: List[str] = [] if os.getenv('NODE_RANK') else logger_list
        self.logger_dict: Dict[Logger] = {name: LOGGERS[name](tracker) for name in logger_list}
        self.logged_artifacts = {}

    def __getitem__(self, item: str) -> Any:
        try:
            return self.logger_dict[item].get_logger_object()
        except KeyError:
            return None

    @property
    def logger_list(self) -> List[Logger]:
        """ Returns logger_dict for backwards compatibility. """
        YAECS_LOGGER.warning("The 'logger_list' property is deprecated and will no longer be supported in future "
                             "releases. Use 'aggregate_logger.logger_dict' instead.")
        return self.logger_dict

    def check_config_requirements(self) -> None:
        """ This checks the config requirements of all loggers. """
        errors = {}
        for name, logger in self.logger_dict.items():
            error = logger.check_config_requirements()
            if error != "":
                errors[name] = error
        if errors:
            formatted_errors = "\n".join([f"    {name.upper()}: {error}" for name, error in errors.items()])
            raise RuntimeError(f"Config Requirement Error : errors were met in the following loggers: {errors.keys()}. "
                               f"Find more details below:\n{formatted_errors}")

    def check_install(self) -> None:
        """ This checks the installation of all loggers. """
        errors = {}
        for name, logger in self.logger_dict.items():
            error = logger.check_install()
            if error != "":
                errors[name] = error
        if errors:
            formatted_errors = "\n".join([f"    {name}: {error}" for name, error in errors.items()])
            raise RuntimeError(f"Installation Error : errors were met in the following loggers: {errors.keys()}. "
                               f"Find more details below:\n{formatted_errors}")

    @property
    def has_loggers(self) -> bool:
        """ Returns whether the aggregate logger has loggers. """
        return bool(self.logger_dict)

    def main_function_context(self) -> list:
        """ Returns a list of context managers that should be used around the main function of the experiment. """
        context_list = []
        for logger in self.logger_dict.values():
            context = logger.main_function_context()
            if isinstance(context, list):
                context_list.extend(context)
            else:
                context_list.append(context)
        return context_list

    def modify_main_function(self, main_function):
        """ Returns a modified version of the main function that should be used instead. """
        for logger in self.logger_dict.values():
            main_function = logger.modify_main_function(main_function)
        return main_function

    def set_attributes(self, logger_attributes: Dict[str, Dict[str, Any]]) -> None:
        """
        Sets logger attributes. These attributes will be used when initialising or using the loggers. Check each
        logger's documentation to see which attributes can be used.

        :param logger_attributes: dictionary mapping logger names to dictionaries of attributes to add to them
        """
        for logger_name, attributes in logger_attributes.items():
            if logger_name in self.logger_dict:
                self.logger_dict[logger_name].set_attributes(attributes)
            else:
                raise ValueError(f"Logger '{logger_name}' not found in aggregate logger. Available loggers are: "
                                 f"{list(self.logger_dict.keys())}.")

    def start_run(self, experiment_name: str, run_name: str, description: str, params: dict) -> None:
        """ Prepares the logger for the start of the run. """
        for logger in self.logger_dict.values():
            logger.start_run(experiment_name, run_name, description, params)

    def log_scalar(self, name: str, value: Union[float, int], step: Optional[int] = None,
                   sub_logger: Optional[str] = None, description: Optional[str] = None,
                   only_loggers: Union[None, str, List[str]] = None,
                   except_loggers: Union[None, str, List[str]] = None) -> None:
        """ Logs a scalar value using the logger. """
        for logger in self._get_loggers(only_loggers, except_loggers):
            logger.log_scalar(name, value, step, sub_logger, description)

    def log_image(self, name: str, image, step: Optional[int] = None, sub_logger: Optional[str] = None,
                  extension: str = "png", only_loggers: Union[None, str, List[str]] = None,
                  except_loggers: Union[None, str, List[str]] = None,
                  maximum: Optional[int] = None, maximum_per_step: Optional[int] = None) -> None:
        """ Logs an image using the logger. The image could be a path to a saved image, matplotlib or plotly figure, a
        PIL.Image, or a n*n*3 numpy array. """
        if self._check_maximums("logged_images", step, maximum, maximum_per_step):
            for logger in self._get_loggers(only_loggers, except_loggers):
                logger.log_image(name, image, step, sub_logger, extension)
            self._add_logged_artifact("logged_images", step)
        else:
            YAECS_LOGGER.debug(f"Image {name} at step {step} was not logged to sub_logger {sub_logger} because the "
                               f"maximum number of images was reached.")

    def _add_logged_artifact(self, artifact_name, step):
        """ Adds an artifact to the logged artifacts. """
        if artifact_name not in self.logged_artifacts:
            self.logged_artifacts[artifact_name] = {step: 1}
        else:
            if step not in self.logged_artifacts[artifact_name]:
                self.logged_artifacts[artifact_name][step] = 1
            else:
                self.logged_artifacts[artifact_name][step] += 1

    def _check_maximums(self, artifact_name, step, maximum, maximum_per_step):
        """ Checks if the maximums have been reached for the given artifact. """
        number = sum(self.logged_artifacts[artifact_name].values()) if artifact_name in self.logged_artifacts else 0
        number_at_step = (0 if number == 0 or step not in self.logged_artifacts[artifact_name]
                          else self.logged_artifacts[artifact_name][step])
        if maximum is not None and number >= maximum >= 0:
            return False
        if maximum_per_step is not None and number_at_step >= maximum_per_step >= 0:
            return False
        return True

    def _get_loggers(self, only_loggers: Union[None, str, List[str]],
                     except_loggers: Union[None, str, List[str]]) -> List[Logger]:
        """ Returns the loggers that should be used for the current function. """
        if only_loggers is None:
            only_loggers = self.logger_dict.keys()
        elif isinstance(only_loggers, str):
            only_loggers = [only_loggers]
        only_loggers = [self.logger_dict[name] for name in only_loggers if name in self.logger_dict]
        if except_loggers is None:
            except_loggers = []
        elif isinstance(except_loggers, str):
            except_loggers = [except_loggers]

        return [logger for logger in only_loggers if not any(logger.name == name for name in except_loggers)]
