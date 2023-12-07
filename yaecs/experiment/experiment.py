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
import logging
import os
from contextlib import ExitStack
from functools import partial
from typing import Any, Callable, List, Optional

from .experiment_utils import format_mode
from .tracker import Tracker
from ..config.config import Configuration

YAECS_LOGGER = logging.getLogger(__name__)


class Experiment:
    """ Class automating tracking using different tracking packages. """

    def __init__(self, config: Configuration, main_function: Callable,
                 experiment_name: Optional[str] = None, run_name: Optional[str] = None,
                 params_filter_fn: Optional[Callable[[Configuration], List[str]]] = None,
                 log_modified_params_only: bool = False, do_not_log_hooks: bool = False,
                 only_params_to_log: Optional[List[str]] = None, params_not_to_log: Optional[List[str]] = None,
                 description_formatter: Optional[Callable[[Optional[str]], str]] = None):
        """
        Creates an instance of the Experiment class, which wraps around a main function.

        :param config: config used for the experiment
        :param main_function: function to run to perform the experiment
        :param experiment_name: name of the experiment, defaults to name
            of the folder set as experiment path in the config
        :param run_name: name of the run, defaults as the index of the run in the experiment folder
        :param params_filter_fn: function to use instead of the default filter to get the list of the names of the
            parameters to log to the tracker from the config. If this is used, then 'log_modified_params_only',
            'only_params_to_log' and 'params_not_to_log' are ignored.
        :param log_modified_params_only: whether the parameters to filter using the other arguments are the parameters
            that changed compared to the default config (True) or only those of the whole config (False)
        :param do_not_log_hooks: whether the parameters defined as hooks should be filtered out (True) or not (False)
        :param only_params_to_log: if provided, only the parameters whose names are given will be filtered and logged
        :param params_not_to_log: if provided, parameters whose names are given will be filtered out
        :param description_formatter: optional function to use to format the provided run description instead of the
            default formatter self.default_formatter
        """
        self.config = config
        self.main_function = main_function
        if not hasattr(self, "number_of_runs"):
            self.number_of_runs = None
        self.current_run = None
        self.format_description = self.default_formatter if description_formatter is None else description_formatter
        tracker_config = self.config.get_hook("tracker_config")
        if len(tracker_config) > 1:
            raise RuntimeError("Several parameters were registered as tracker configs. Please register only one.")
        self.tracker = Tracker(self.config[tracker_config[0]] if tracker_config else {"type": ""},
                               self, experiment_name=experiment_name, run_name=run_name, starting_step=0,
                               params_filter_fn=params_filter_fn, log_modified_params_only=log_modified_params_only,
                               do_not_log_hooks=do_not_log_hooks, only_params_to_log=only_params_to_log,
                               params_not_to_log=params_not_to_log)

    def default_formatter(self, description: Optional[str]) -> str:
        """
        This function formats the provided description before passing it to the trackers.

        :param description: provided description to format. You can use flags in the description, which will be used
            during formatting.
            - `%h` (can be used once in the description) : Everything before this tag will be considered the header of
              the description
            - `%m` : Will be replaced by the mode of the experiment (train, test, etc.)
            - `%n` : Will be replaced by the name of the experiment
            - `%p` : Will be replaced by the path of the experiment
            - '%v' : Will be replaced by the variation name of the experiment
        :raises RuntimeError: when more than one header tag is detected in the description
        :return: formatted description
        """
        # Setup
        try:
            experiment_path = self.config.get_experiment_path()
        except RuntimeError:
            experiment_path = None
        mode_param = self.config.get_hook("mode")
        mode = format_mode(self.config[mode_param[0]]) if mode_param else "unspecified mode"
        description = description if description else "unstated purpose"
        if "%n" in description:
            name = None if experiment_path is None else os.path.basename(experiment_path)
            description = description.replace("%n", str(name))
        if "%p" in description:
            description = description.replace("%p", str(experiment_path))
        if "%m" in description:
            description = description.replace("%m", str(mode))
        if "%v" in description:
            description = description.replace("%v", str(self.config.get_variation_name()))

        # Header
        header = "Run" + ("" if experiment_path is None else f" in {experiment_path}")
        if mode != "unspecified mode":
            header = f"{mode} r{header[1:]}"
        if "%h" in description:
            if description.count("%h") > 1:
                raise RuntimeError("You can only declare one header in the run description.")
            header, description = description.split('%h')
        header = header[0].capitalize() + header[1:]

        # Final description
        description = f"{header}\nPurpose : {description}"
        if self.number_of_runs > 1:
            description = f"[{self.current_run + 1}/{self.number_of_runs}] {description}"
        return description

    def run(self, run_description: Optional[str] = None, **kwargs) -> Any:
        """
        Creates all variations of the config and starts a run for each of them.

        :param run_description: if passed, will serve as a description for the purpose of the current run. This
            description will be formatted using either the default formatter or a formatter passed when creating the
            Experiment object. With the default formatter, you can use flags in the description, which will be used
            during formatting.
            - `%h` (can be used once in the description) : Everything before this tag will be considered the header of
              the description
            - `%m` : Will be replaced by the mode of the experiment (train, test, etc.)
            - `%n` : Will be replaced by the name of the experiment
            - `%p` : Will be replaced by the path of the experiment
            - '%v' : Will be replaced by the variation name of the experiment
        :param kwargs: arguments to pass to the main function aside from the config and the tracker
        :return: whatever the main function returns
        """
        variations = self.config.create_variations()
        self.number_of_runs = len(variations)
        description = run_description
        returns = []
        for run_number, variation in enumerate(variations):
            self.current_run = 0
            variation_description = description
            if variation is not self.config:
                filter_fn = (None if self.tracker.get_filtered_params is self.tracker.default_filter
                             else self.tracker.get_filtered_params)
                format_fn = None if self.format_description is self.default_formatter else self.format_description
                self.__init__(config=variation,  # pylint: disable=unnecessary-dunder-call
                              main_function=self.main_function, experiment_name=self.tracker.experiment_name,
                              run_name=self.tracker.run_name, params_filter_fn=filter_fn,
                              log_modified_params_only=self.tracker.log_modified_params_only,
                              only_params_to_log=self.tracker.only_params if filter_fn is None else None,
                              params_not_to_log=self.tracker.except_params if filter_fn is None else None,
                              description_formatter=format_fn)
                self.current_run = run_number
                description = (input("[TRACKER] Please describe the purpose of these runs : ")
                               if description is None else description)
                description = description if description else "unstated purpose"
                if description.count("%h") == 1:
                    variation_description = (f"{description.split('%h')[0]} (variation %v)%h"
                                             f"{description.split('%h')[1]}")
                else:
                    variation_description = f"%m run in %p (variation %v) :%h{description}"
            returns.append(self.run_single(variation_description, **kwargs))
        return returns

    def run_single(self, run_description: Optional[str] = None, **kwargs) -> Any:
        """
        Runs a single experiment with the defined config. Does not check the config variations.

        :param run_description: if passed, will serve as a description for the purpose of the current run. This
            description will be formatted using either the default formatter or a formatter passed when creating the
            Experiment object. With the default formatter, you can use flags in the description, which will be used
            during formatting.
            - `%h` (can be used once in the description) : Everything before this tag will be considered the header of
              the description
            - `%m` : Will be replaced by the mode of the experiment (train, test, etc.)
            - `%n` : Will be replaced by the name of the experiment
            - `%p` : Will be replaced by the path of the experiment
            - '%v' : Will be replaced by the variation name of the experiment
        :param kwargs: arguments to pass to the main function aside from the config and the tracker
        :return: whatever the main function returns
        """
        # Start the run
        if os.getenv('NODE_RANK'):  # do not track if in a pytorch-lightning spawned process
            description = None
        else:
            description = (input("[TRACKER] Please describe the purpose of this run : ")
                           if run_description is None else run_description)
            description = self.format_description(description)
        self.tracker.start_run(description=description)

        # Function and context preparation
        main_function = partial(self.main_function, config=self.config, tracker=self.tracker, **kwargs)
        main_function.__name__ = self.main_function.__name__  # partial functions do not have names
        main_function = self.tracker.loggers.modify_main_function(main_function)
        contexts = self.tracker.loggers.main_function_context()

        # Run
        with ExitStack() as stack:
            for context in contexts:
                stack.enter_context(context)
            to_return = main_function()
        return to_return
