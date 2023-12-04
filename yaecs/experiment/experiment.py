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
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from mock import patch

from .timer import TimerManager
from ..config.config import Configuration
from ..yaecs_utils import add_to_csv, compare_string_pattern, lazy_import, new_print, NoValue

# ClearML integration, see original package : https://clear.ml
clearml = lazy_import("clearml")  # pylint: disable=invalid-name
# MLFlow integration, see original package : https://mlflow.org
mlflow = lazy_import("mlflow")  # pylint: disable=invalid-name
# Sacred integration, see original package : https://sacred.readthedocs.io/
sacred = lazy_import("sacred")  # pylint: disable=invalid-name
# Tensorboard integration, see original package : https://www.tensorflow.org/tensorboard
tensorflow = lazy_import("tensorflow")  # pylint: disable=invalid-name

YAECS_LOGGER = logging.getLogger(__name__)


class Experiment:
    """ Class automating tracking using different tracking packages. """

    def __init__(self, config: Configuration, main_function: Callable,
                 experiment_name: Optional[str] = None, run_name: Optional[str] = None,
                 params_filter_fn: Optional[Callable[[Configuration],
                                                     List[str]]] = None, log_modified_params_only: bool = True,
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
                               self, experiment_name=experiment_name, run_name=run_name,
                               params_filter_fn=params_filter_fn, log_modified_params_only=log_modified_params_only,
                               only_params_to_log=only_params_to_log, params_not_to_log=params_not_to_log)

    def default_formatter(self, description: Optional[str]) -> str:
        """
        This function formats the provided description before passing it to the trackers.

        :param description: provided description to format. You can use the tag `%h` once in the description. Everything
            before this tag will be considered the header of the description
        :raises RuntimeError: when more than one header tag is detected in the description
        :return: formatted description
        """
        description = description if description else "unstated purpose"
        header = ""
        if "%h" in description:
            if description.count("%h") > 1:
                raise RuntimeError("You can only declare one header in the run description.")
            header, description = description.split('%h')
            header = f"[{self.current_run + 1}/{self.number_of_runs}] {header}\n"
        description = f"{header}Purpose : {description}"
        return description

    def run(self, run_description: Optional[str] = None, **kwargs) -> Any:
        """
        Creates all variations of the config and starts a run for each of them.

        :param run_description: if passed, will serve as a description for the purpose of the current run. You can use
            the tag %h once in the description. Everything before this tag will be considered the header
            of the description
        :param kwargs: arguments to pass to the main function aside from the config and the tracker
        :return: whatever the main function returns
        """
        variations = self.config.create_variations()
        self.number_of_runs = len(variations)
        description = run_description
        returns = []
        for run_number, variation in enumerate(variations):
            self.current_run = 0
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
                    description = f"{description.split('%h')[0]} (variation {variation.get_variation_name()})%h" \
                                  f"{description.split('%h')[1]}"
                else:
                    description = f"Variation {variation.get_variation_name()}%h{description}"
            returns.append(self.run_single(description, **kwargs))
        return returns

    def run_single(self, run_description: Optional[str] = None, **kwargs) -> Any:
        """
        Runs a single experiment with the defined config. Does not check the config variations.

        :param run_description: if passed, will serve as a description for the purpose of the current run. You can use
            the tag %h once in the description. Everything before this tag will be considered the header
            of the description
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


class Tracker:
    """ Class created by Experiment to log values. """

    def __init__(self, tracker_config: Dict[str, Any], experiment: Experiment, experiment_name: Optional[str] = None,
                 run_name: Optional[str] = None, starting_step: int = 0, params_filter_fn: Optional[Callable] = None,
                 log_modified_params_only: bool = True, only_params_to_log: Optional[List[str]] = None,
                 params_not_to_log: Optional[List[str]] = None):
        """
        Reads the tracker config from the general config to create a Tracker object used for logging during the run.

        :param tracker_config: tracker config from the general config
        :param experiment: passed automatically from the instance of Experiment this tracker originates from
        :param experiment_name: name for the experiment (inferred from the experiment path if not provided)
        :param run_name: name for the run (inferred from the experiment path if not provided)
        :param starting_step: step at which to start logging scalars
        :param params_filter_fn: function to use instead of the default filter to get the list of the names of the
            parameters to log to the tracker from the config. If this is used, then 'log_modified_params_only',
            'only_params_to_log' and 'params_not_to_log' are ignored.
        :param log_modified_params_only: whether the parameters to filter using the other arguments are the parameters
            that changed compared to the default config (True) or only those of the whole config (False)
        :param only_params_to_log: if provided, only the parameters whose names are given will be filtered and logged
        :param params_not_to_log: if provided, parameters whose names are given will be filtered out
        """
        # General attributes
        self.config = {k: v for k, v in tracker_config.items() if k != "type"}
        loggers = self.config.get("sub_loggers", [])
        self.sub_loggers = [""] + (loggers if isinstance(loggers, list) else [loggers])
        self.experiment = experiment
        self.experiment_name = experiment_name
        self.run_name = run_name
        self._step = starting_step
        self.timer = TimerManager()
        self.loggers = {k: None for k in ACCEPTED_TRACKERS}
        self.sub_loggers = [""]
        self.basic_logger = None
        if "basic" in self.types:
            try:
                self.basic_logger = self.experiment.config.get_experiment_path()
            except RuntimeError:
                self.basic_logger = self.config.get("basic_logdir", None)

        # Parameters filtering
        self.get_filtered_params = self.default_filter if params_filter_fn is None else params_filter_fn
        self.log_modified_params_only = log_modified_params_only
        self.only_params = None
        if only_params_to_log is not None:
            if params_filter_fn is not None:
                YAECS_LOGGER.warning("WARNING : parameter 'only_params_to_log' is ignored when 'params_filter_fn' is "
                                     "provided.")
            self.only_params = only_params_to_log if isinstance(only_params_to_log, list) else [only_params_to_log]
        self.except_params = []
        if params_not_to_log is not None:
            if params_filter_fn is not None:
                YAECS_LOGGER.warning("WARNING : parameter 'params_not_to_log' is ignored when 'params_filter_fn' is "
                                     "provided.")
            self.except_params = params_not_to_log if isinstance(params_not_to_log, list) else [params_not_to_log]

    def default_filter(self, config: Configuration) -> List[str]:
        """
        Default parameters filtering function. Uses the pre-defined 'log_modified_params_only', 'only_params' and
        'except_params' attributes to filter out the parameters of the config.
        It starts with a list of all the params which were modified from the default config, except if
        log_modified_params_only was set to False in which case it starts from all the parameters in the config. Then,
        it filters out all hooks, then all parameters in except_params, and finally only keeps those that are also in
        only_params.

        :param config: instance of Configuration from which to filter the parameters
        :return: the list of the filtered parameters names
        """
        # Get params to filter
        if self.log_modified_params_only:
            default = config.__class__.build_from_configs(config.config_metadata["config_hierarchy"][0],
                                                          do_not_post_process=True, do_not_merge_command_line=True,
                                                          verbose=False)
            diff = default.compare(config, reduce=True)
        else:
            diff = list(config.get_dict(deep=True).items())

        # Get filters
        filters = list(self.except_params)
        for hooks in config.get_hook().values():
            filters += hooks

        # Perform filtering
        to_ret = []
        for name in diff:
            if self.only_params is None or any(
                    compare_string_pattern(config.match_params("*" + name[0])[0], pattern)
                    for pattern in self.only_params):
                if not any(
                        compare_string_pattern(config.match_params("*" + name[0])[0], pattern) for pattern in filters):
                    to_ret.append(name[0])
        return to_ret

    def extract_names(self) -> Tuple[str, str]:
        """
        Gets experiment and run names, using either names given when instantiating the Experiment (if provided) or
        inferring them from the config's experiment path. If nothing is provided and no experiment path is defined,
        raises an error.

        :raises RuntimeError: if no experiment path is defined in the config and no experiment or run name is provided
        :return: the experiment name and the run name
        """
        try:
            name_from_config = self.experiment.config.get_experiment_path()
        except RuntimeError:
            name_from_config = None
        if name_from_config is None and self.experiment_name is None:
            raise RuntimeError("Please specify an experiment name either by "
                               "registering a parameter as experiment path "
                               "with the 'register_as_experiment_path' method, "
                               "or by passing it when creating your experiment object.")
        if name_from_config is None and self.run_name is None:
            raise RuntimeError("Please specify a run name either by "
                               "registering a parameter as experiment path "
                               "with the 'register_as_experiment_path' method, "
                               "or by passing it when creating your experiment object.")
        if self.experiment_name is None:
            if self.experiment.config.get_variation_name() is None:
                exp_name = "_".join(name_from_config.split(os.sep)[-1].split("_")[:-1])
            else:
                exp_name = "_".join(name_from_config.split(os.sep)[-2].split("_")[:-1])
        else:
            exp_name = self.experiment_name
        if self.run_name is None:
            if self.experiment.config.get_variation_name() is None:
                run_name = name_from_config.split(os.sep)[-1].split("_")[-1]
            else:
                run_name = name_from_config.split(os.sep)[-2].split("_")[-1] + "_" + name_from_config.split(os.sep)[-1]
        else:
            run_name = self.run_name
        return exp_name, run_name

    def start_run(self, description: Optional[str] = None) -> None:
        """
        Initialises the configured loggers, which most of the time means preparing their logger in self.loggers.
        """
        experiment_name, run_name = self.extract_names()
        config = self.experiment.config
        params_to_log = {k: config[config.match_params("*" + k)[0]] for k in self.get_filtered_params(config)}
        self.loggers.start_run(experiment_name, run_name, description, params_to_log)

    def step(self, step: Optional[int] = None, auto_log_timers: bool = True, print_timers: bool = True) -> None:
        """
        Increments the step counter.

        :param step: step to increment to. If None, will increment to the next step
        :param auto_log_timers: whether to automatically log the timers at the end of the step
        :param print_timers: whether to print the timers at the end of the step
        """
        if step is not None and step < self._step:
            raise ValueError(f"Cannot go back to step {step} from step {self._step}.")
        if auto_log_timers:
            timers = {"timers/" + name: duration for name, duration in self.timer["last"].items()
                      if duration is not None}
            self.log_scalars(timers, step=self._step)
        if print_timers:
            print(self.timer.render(which_step="last"))
        self._step = self._step + 1 if step is None else step

        if "mlflow" in self.types:
            mlflow.set_tracking_uri(self.config["tracking_uri"])
            mlflow.set_experiment(experiment_name)
            self.loggers["mlflow"] = mlflow.start_run(run_name=run_name, description=description)
            mlflow.log_params(params_to_log)

        if "tensorboard" in self.types:
            if "%e" not in self.config["logdir"]:
                writer_path = os.path.join(self.config["logdir"], experiment_name, run_name)
            else:
                writer_path = self.config["logdir"].replace("%e", self.experiment.config.get_experiment_path())
            self.loggers["tensorboard"] = {
                sub_logger: tensorflow.summary.create_file_writer(os.path.join(writer_path, sub_logger))
                for sub_logger in self.sub_loggers}

        if "clearml" in self.types:
            self.loggers["clearml"] = clearml.Task.init(project_name=self.config["project_name"],
                                                        task_name=f"{experiment_name}/{run_name}",
                                                        continue_last_task=bool(os.getenv("PICKUP")))
            self.loggers["clearml"].set_comment(description)
            self.loggers["clearml"].connect(self.experiment.config.get_dict(deep=True))

    def start_timer(self, name: str = "MyTimer", step: Union[NoValue, None, int] = NoValue(),
                    verbose: Optional[int] = None) -> None:
        """
        Starts a timer.

        :param name: name of the timer
        :param step: starting step (if None, assumes step=last stop step, timings are averages over the elapsed steps)
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail
        """
        step = self._step if isinstance(step, NoValue) else step
        if name in self.timer.timers and self.timer.timers[name].running:
            self.stop_timer(name, step, verbose)
        self.timer.start(name, step, verbose)

    def stop_timer(self, name: str = "MyTimer", step: Optional[int] = None, verbose: Optional[int] = None) -> None:
        """
        Stops a timer.

        :param name: name of the timer
        :param step: starting step (if None, assumes step=start step + 1, timings are averages over the elapsed steps)
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail
        """
        step = self._step if isinstance(step, NoValue) else step
        if name in self.timer.timers and self.timer.timers[name].running:
            start_step = self.timer.timers[name].start_times[-1][1]
            step = step if step > start_step else start_step + 1
        self.stop_timer(name, step, verbose)

    def step(self, step: Optional[int] = None, auto_log_timers: bool = True, print_timers: bool = True) -> None:
        """
        Increments the step counter.

        :param step: step to increment to. If None, will increment to the next step
        :param auto_log_timers: whether to automatically log the timers at the end of the step
        :param print_timers: whether to print the timers at the end of the step
        """
        if step is not None and step < self._step:
            raise ValueError(f"Cannot go back to step {step} from step {self._step}.")
        if auto_log_timers:
            timers = {"timers/" + name: duration for name, duration in self.timer["last"] if duration is not None}
            self.log_scalars(timers, step=self._step)
        if print_timers:
            print(self.timer.render(which_step="last"))
        self._step = self._step + 1 if step is None else step

    def log_scalar(self, name: str, value: Union[float, int], step: Union[NoValue, None, int] = NoValue(),
                   sub_logger: Optional[str] = None, description: Optional[str] = None,
                   main_process_only: bool = False) -> None:
        """
        Logs the given value under the given name at given step in the configured trackers. The description is optional
        and can only be used if the tracker is tensorboard.

        :param name: name for the value to be logged
        :param value: value to be logged
        :param step: step at which the value is logged. If set to None or a negative value, will default to 0 for the
            tensorboard tracker, will default to -1 for the basic tracker and will be logged as a "single value" for the
            clearml tracker. If not provided, will default to the current step of the tracker (0 by default)
        :param sub_logger: if specified, logs to corresponding sub-logger. Can be interpreted as a sub-folder for the
            scalar name most of the time, but in the case of tensorboard will actually use a different summary writer
        :param description: only used for the tensorboard tracker, corresponds to a short description of the value
        :param main_process_only: do not try to log in pytorch-lightning sub-processes
        """
        step = self._step if isinstance(step, NoValue) else step
        if not main_process_only or not os.getenv('NODE_RANK'):  # do not track in a pytorch-lightning spawned process
            self._warn_if_no_logs()
            self.loggers.log_scalar(name, value, step=step, sub_logger=sub_logger, description=description)

    def log_scalars(self, dictionary: Dict[str, Any], step: Union[NoValue, None, int] = NoValue(),
                    sub_logger: Optional[str] = None, main_process_only: bool = False) -> None:
        """
        Logs several values contained in a dictionary, one by one using Tracker.log_scalar.

        :param dictionary: dictionary containing the (name, value) pairs to be logged
        :param step: step at which the value is logged. If not provided, will default to 0 for the tensorboard tracker,
            will default to -1 for the basic tracker and will be logged as a "single value" for the clearml tracker
        :param sub_logger: if specified, logs to corresponding sub-logger. Can be interpreted as a sub-folder for the
            scalar name most of the time, but in the case of tensorboard will actually use a different summary writer
        :param main_process_only: do not try to log in pytorch-lightning sub-processes
        """
        if not main_process_only or not os.getenv('NODE_RANK'):  # do not track in a pytorch-lightning spawned process
            self._warn_if_no_logs()
            for key, value in dictionary.items():
                self.log_scalar(key, value, step=step, sub_logger=sub_logger)

    def start_timer(self, name: str = "MyTimer", step: Union[NoValue, None, int] = NoValue(),
                    verbose: Optional[int] = None) -> None:
        """
        Starts a timer.

        :param name: name of the timer
        :param step: Step at which to log the measured duration. If not provided, uses the internal step. If None,
            assumes step=previous stop step.
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail
        """
        step = self._step if isinstance(step, NoValue) else step
        if name in self.timer.timers and self.timer.timers[name].running:
            self.stop_timer(name, step, verbose)
        self.timer.start(name, step, verbose)

    def stop_timer(self, name: str = "MyTimer", step: Union[NoValue, None, int] = NoValue(),
                   verbose: Optional[int] = None) -> None:
        """
        Stops a timer.

        :param name: name of the timer
        :param step: Step at which to log the measured duration. If not provided, uses the internal step. If None,
            assumes step=previous start step + 1.
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail
        """
        step = self._step if isinstance(step, NoValue) else step
        if name in self.timer.timers and self.timer.timers[name].running:
            start_step = self.timer.timers[name].start_times[-1][1]
            step = step if step > start_step else start_step + 1
        self.stop_timer(name, step, verbose)

    def measure_time(self, name: str = "MyTimer", step: Union[NoValue, None, int] = NoValue(),
                     verbose: Optional[int] = None) -> None:
        """
        Returns an instanciated context manager to time a block of code.

        :param name: name of the timer
        :param step: Step at which to log the measured duration. If not provided, uses the internal step. If None,
            assumes step=previous stop step
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail
        :return: context manager to time a block of code
        """
        step = self._step if isinstance(step, NoValue) else step
        return TimeInContext(timer_manager=self.timer, name=name, step=step, verbose=verbose)

    def _warn_if_no_logs(self):
        if not self.loggers.has_loggers:
            YAECS_LOGGER.warning("WARNING : no tracker configured, scalars will not be logged anywhere.")
            if os.getenv('NODE_RANK'):
                YAECS_LOGGER.warning("This is because trackers are deactivated in pytorch-lightning processes.\n"
                                     "To suppress this message, pass 'main_process_only=True'.")
