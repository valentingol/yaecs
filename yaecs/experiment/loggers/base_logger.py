""" This file defines the base class for all loggers, as well as the LoggerList class to compose loggers. """
import logging
from typing import Any, Optional, Union

YAECS_LOGGER = logging.getLogger(__name__)


class Logger:
    """ Base class for all loggers. Loggers are interfaces to utilities like ClearML, Tensorboard, etc., accessed
    by Experiment and Tracker objects communicate with those utilities. """
    def __init__(self, name: str, tracker):
        self.name = name
        self.tracker = tracker
        self.argument_warnings = set()

    def check_config_requirements(self) -> str:
        """ This returns an empty string if the tracker config and general config satisfy the logger's requirements,
        otherwise the error message if the requirements are not satisfied. """
        return ""

    def check_install(self) -> str:
        """ This returns an empty string if the logger is installed properly, otherwise the error message if the logger
        is not installed properly. """
        return ""

    def get_logger_object(self) -> Any:
        """ Returns the main object repsonsible for the logging activities. """
        return None

    def main_function_context(self):
        """ Returns a context manager or list that should be used around the main function of the experiment. """
        return NoContext(tracker=self.tracker)

    def modify_main_function(self, main_function):
        """ Returns a modified version of the main function that should be used instead. """
        return main_function

    def start_run(self, experiment_name: str, run_name: str, description: str, params: dict) -> None:
        """ Prepares the logger for the start of the run. """
        raise NotImplementedError

    def log_scalar(self, name: str, value: Union[float, int], step: Optional[int] = None,
                   sub_logger: Optional[str] = None, description: Optional[str] = None) -> None:
        """ Logs a scalar value using the logger. """
        raise NotImplementedError

    def log_image(self, name: str, image: Any, step: Optional[int] = None, sub_logger: Optional[str] = None,
                  extension: str = "png") -> None:
        """ Logs an image using the logger. The image could be a path to a saved image, matplotlib or plotly figure, a
        PIL.Image, or a n*n*3 numpy array. """
        raise NotImplementedError

    def _warn_function_argument(self, function_name: str, argument_name: str, argument_value: Any, default_value: Any):
        """ If the user changed the default value, warns the user that a certain argument is not supported by given
        logger, then stores it to avoid repeating the warning. """
        if argument_value != default_value:
            index = function_name + argument_name
            if index not in self.argument_warnings:
                YAECS_LOGGER.warning(f"WARNING : in {function_name} : '{argument_name}' is not used in Logger "
                                     f"{self.name}.")
                self.argument_warnings.add(index)


class NoContext:
    """ A context manager that does nothing. """
    def __init__(self, tracker):
        self.tracker = tracker

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass
