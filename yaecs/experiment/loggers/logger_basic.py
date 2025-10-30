""" This file defines the class for the basic logger. """
import logging
import os
from shutil import copyfile
import sys
import traceback
from typing import Any, Optional, Union

from mock import patch

from .base_logger import Logger
from .logger_utils import NotImportedModule, add_to_csv, new_print

try:
    import matplotlib
except ImportError:
    matplotlib = NotImportedModule("matplotlib")
try:
    import numpy as np
except ImportError:
    np = NotImportedModule("numpy")
try:
    from PIL import Image
except ImportError:
    Image = NotImportedModule("PIL")
try:
    import plotly
except ImportError:
    plotly = NotImportedModule("plotly")

YAECS_LOGGER = logging.getLogger(__name__)


class BasicLogger(Logger):
    """
    Basic Logger. This logger logs everything needed, albeit in a very simple way.
    Attributes list: [].
    """

    def __init__(self, tracker):
        super().__init__("Basic Logger", tracker)
        self.possible_attributes = []
        self.path = None

    def check_config_requirements(self) -> str:
        try:
            self.path = self.tracker.experiment.config.get_experiment_path()
        except RuntimeError:
            self.path = self.tracker.config.get("basic_logdir", None)
        if self.path is None:
            error = ("Config Requirement Error : no path was provided for the basic logger. Provide one using an "
                     "experiment path in the config or by setting the basic_logdir key in the tracker config.")
            return error
        return ""

    def get_logger_object(self) -> Any:
        return self.path

    def main_function_context(self):
        basic_tracker_context = BasicTrackerContext(self.path,
                                                    self.tracker.experiment.number_of_runs,
                                                    self.tracker.experiment.current_run)
        return [basic_tracker_context, patch('builtins.print', side_effect=new_print)]

    def start_run(self, experiment_name: str, run_name: str, description: str, params: dict) -> None:
        self.tracker.experiment.config.save(os.path.join(self.path, "config.yaml"))
        with open(os.path.join(self.path, "comments.txt"), 'w') as file:
            file.write(description)

    def log_scalar(self, name: str, value: Union[float, int], step: Optional[int] = None,
                   sub_logger: Optional[str] = None, description: Optional[str] = None) -> None:
        self._warn_function_argument("log_scalar", "description", description, None)
        extended_name = name
        if sub_logger is not None:
            extended_name = f"{sub_logger}/{extended_name}"
        add_to_csv(os.path.join(self.path, "logged_scalars.csv"),
                   extended_name, value, -1 if step is None else step)

    def log_image(self, name: str, image: Any, step: Optional[int] = None, sub_logger: Optional[str] = None,
                  extension: str = "png") -> None:
        # Paths and names
        directory = [self.path, "images"]
        if sub_logger:
            directory.append(sub_logger)
        if os.path.dirname(name):
            directory.append(os.path.dirname(name))
        if step is not None:
            directory.append(f"step_{step}")
        os.makedirs(image_path := os.path.join(*directory), exist_ok=True)
        output_path = os.path.join(image_path, f"{os.path.basename(name)}.{extension}")

        # Logging
        if isinstance(image, str):
            if not os.path.isfile(image):
                raise FileNotFoundError(f"Cannot log image '{image}' : path does not exist !")
            copyfile(image, output_path[:-len(extension)] + image.split(".")[-1])
        elif isinstance(image, np.ndarray):
            Image.fromarray(image.astype(np.uint8)).save(output_path)
        elif isinstance(image, Image.Image):
            image.save(output_path)
        elif isinstance(image, matplotlib.figure.Figure):
            image.savefig(output_path)
        elif isinstance(image, plotly.graph_objs.Figure):
            plotly.io.write_image(image, output_path)
        else:
            YAECS_LOGGER.warning(f"WARNING : image {name} at step {step} was not logged to sub_logger {sub_logger} : "
                                 f"unrecognised type {type(image)}.")


class BasicTrackerContext:
    """ Class used to set up the context for YAECS' basic tracker """

    def __init__(self, logger_path: str, runs: Optional[int], current: Optional[int]):
        """
        Initialises a context used to declare the loggers required by the basic tracker.

        :param logger_path: path used by the basic tracker to log
        :param runs: number of runs in the experiment
        :param current: index of current run from 0 to runs-1
        """
        self.runs, self.current = runs, current
        self.logging_handlers = [logging.FileHandler(os.path.join(logger_path, "stdout.log")),
                                 logging.StreamHandler(sys.stdout)]
        self.logging_handlers[0].setFormatter(logging.Formatter(fmt="%(asctime)s : [TRACKER] %(message)s"))
        self.logging_handlers[1].setFormatter(logging.Formatter(fmt="[TRACKER] %(message)s"))
        self.config_handler = logging.FileHandler(os.path.join(logger_path, "stdout.log"))
        self.config_handler.setFormatter(logging.Formatter(fmt="%(asctime)s : [CONFIG] %(message)s"))
        if "pytorch_lightning" in logging.root.manager.loggerDict:
            if not logging.getLogger("pytorch_lightning").propagate:
                self.pytorch_handler = logging.FileHandler(
                    os.path.join(logger_path, "stdout.log"))
                self.pytorch_handler.setFormatter(logging.Formatter(fmt="%(asctime)s : [%(levelname)s] %(message)s"))
        self.print_handlers = [logging.FileHandler(os.path.join(logger_path, "stdout.log")),
                               logging.StreamHandler(sys.stdout)]
        self.print_handlers[0].setFormatter(logging.Formatter(fmt="%(asctime)s : [%(levelname)s] %(message)s"))

    def __enter__(self):
        # Setting up YAECS loggers
        for handler in self.logging_handlers:
            logging.getLogger().addHandler(handler)
        logging.root.setLevel(logging.INFO)
        run_count = ("" if self.runs is None or self.current is None or self.runs == 1
                     else f" {self.current + 1}/{self.runs}")
        logging.root.info(f"Starting experiment{run_count}...\n")
        y_logger = logging.getLogger("yaecs")
        if not y_logger.propagate:
            y_logger.addHandler(self.config_handler)

        # Setting up external modules' compatibility loggers
        if "pytorch_lightning" in logging.root.manager.loggerDict:
            pl_logger = logging.getLogger("pytorch_lightning")
            if not pl_logger.propagate:
                pl_logger.addHandler(self.pytorch_handler)

        # Setting up print catcher
        print_catcher = logging.getLogger("yaecs.print_catcher")
        print_catcher.propagate = False
        for handler in self.print_handlers:
            print_catcher.addHandler(handler)

    def __exit__(self, exc_type, exc_val, exc_tb):
        print_catcher = logging.getLogger("yaecs.print_catcher")

        # Logging error
        if exc_type is not None:
            message_lines = traceback.format_exc().split("\n")
            print_catcher.error("\n".join([message_lines[0]] + message_lines[3:]))

        # Unsetting print catcher
        ([h for h in print_catcher.handlers if isinstance(h, logging.FileHandler)][0]).setFormatter(
            logging.Formatter(fmt="%(message)s"))
        print_catcher.info("")
        logging.root.info("Experiment has concluded !")
        print_catcher.propagate = True
        for handler in self.print_handlers:
            print_catcher.removeHandler(handler)

        # Unsetting YAECS loggers
        for handler in self.logging_handlers:
            logging.getLogger().removeHandler(handler)
        logging.getLogger("yaecs").removeHandler(self.config_handler)

        # Unsetting external modules' compatibility loggers
        if "pytorch_lightning" in logging.root.manager.loggerDict:
            logging.getLogger("pytorch_lightning").removeHandler(self.pytorch_handler)
