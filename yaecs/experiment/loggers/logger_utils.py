""" Defines common functions for logger objects. """
from bisect import bisect
import io
import logging
import os
import sys
from typing import Any

YAECS_LOGGER = logging.getLogger(__name__)


class NotImportedModule:
    """ Class to replace a module that is not installed. When trying to access a member, raises an error. """
    def __init__(self, name: str):
        """
        Initializes the class.

        :param name: name of the module that is not installed
        """
        self.__name = name

    def __getattribute__(self, item):
        if item == "_NotImportedModule__name":
            return object.__getattribute__(self, item)
        raise ModuleNotFoundError(f"Module {self.__name} is not installed. If you want to use this feature, please "
                                  "install it.")


def add_to_csv(csv_path: str, name: str, value: Any, step: int) -> None:
    """
    Adds a logged value to the csv containing previously logged values

    :param csv_path: path to the csv containing the logged values
    :param name: name of the value to log
    :param value: value of the value to log
    :param step: step for which to log the value
    """
    if os.path.isfile(csv_path):
        with open(csv_path, encoding='utf-8') as csv_file:
            data = csv_file.readlines()
            steps = [int(d.split(",")[0]) for d in data[1:]]
            metrics = [d.strip("\n") for d in data[0].split(",")[1:]]
            values = [[d.split(",")[1 + i].strip("\n") if d.split(",")[1 + i] else ""
                       for d in data[1:]] for i in range(len(metrics))]
    else:
        steps = []
        metrics = []
        values = []
    if name not in metrics:
        metrics.append(name)
        values.append(["" for _ in range(len(steps))])
    if step not in steps:
        index = bisect(steps, step)
        steps.insert(index, step)
        for i, metric in enumerate(metrics):
            values[i].insert(index, str(value) if metric == name else "")
    else:
        values[metrics.index(name)][steps.index(step)] = str(value)

    with open(csv_path, 'w', encoding='utf-8') as csv_file:
        csv_file.write(",".join(["steps"] + metrics) + "\n")
        for index, step_to_log in enumerate(steps):
            data = [str(step_to_log)] + [v[index] for v in values]
            csv_file.write(",".join(data) + "\n")


def new_print(*args, sep: str = " ", end: str = "", file: io.TextIOWrapper = None, **keywords) -> None:
    """
    Replaces the builtin print function during an experiment run such that printed messages are also logged. Please note
    that the default file (None) logs to logging's root logger which will always go to the next line after each message.
    Therefore, the 'end' param does not replace \\n as usual, but adds a suffix after the message and before the \\n.

    :param args: objects to print
    :param sep: how to separate the different objects
    :param end: suffix to add after the message
    :param file: file to print to, defaults to a logging to logging's root logger with level logging.INFO
    :param keywords: might contain 'flush', in which case raise an error
    :raises TypeError: when the keyword arguments contain 'flush'
    """
    if not os.getenv('NODE_RANK'):  # do not print if in a pytorch-lightning spawned process
        if "flush" in keywords:
            YAECS_LOGGER.warning("Because YAECS uses logging.info to log messages logged via the print function, the "
                                 "'flush' parameter is not supported for the print function within your main.")
        message = sep.join([str(a) for a in args]) + end.strip()
        if message.strip():
            if file is not None and file is not sys.stdout:
                file.write(message)
            logging.getLogger("yaecs.print_catcher").info(message)


def value_to_float(value: Any, logger_name: str, value_name: str) -> str:
    """ Converts a value to a float if possible, otherwise raises a warning and returns an empty string. """
    try:
        value = float(value)
    except ValueError:
        YAECS_LOGGER.warning(f"WARNING : will not log non-float value '{value_name}': {value} to {logger_name} logger.")
        return ""
    if not isinstance(value, (float, int)):
        YAECS_LOGGER.warning(f"WARNING : logging non-float value '{value_name}': {value} to {logger_name} logger.\name"
                             "Logging non-float values can cause unexpected time or space complexity in some loggers.")
    return value
