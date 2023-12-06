""" This file defines the experiment tracker object, which for an experiment handles all tracking and logging
activities. """
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .timer import TimerManager, TimeInContext
from .loggers.aggregate_logger import AggregateLogger
from ..config.config import Configuration
from ..yaecs_utils import compare_string_pattern, NoValue

YAECS_LOGGER = logging.getLogger(__name__)


class Tracker:
    """ Class created by Experiment to log values. """

    def __init__(self, tracker_config: Dict[str, Any], experiment, experiment_name: Optional[str] = None,
                 run_name: Optional[str] = None, starting_step: int = 0, params_filter_fn: Optional[Callable] = None,
                 log_modified_params_only: bool = False, do_not_log_hooks: bool = False, 
                 only_params_to_log: Optional[List[str]] = None, params_not_to_log: Optional[List[str]] = None):
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
        :param do_not_log_hooks: whether the parameters defined as hooks should be filtered out (True) or not (False)
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

        # AggregateLogger
        self.loggers = AggregateLogger(self, tracker_config.get("type", []))
        self.loggers.check_install()
        self.loggers.check_config_requirements()

        # Parameters filtering
        self.get_filtered_params = self.default_filter if params_filter_fn is None else params_filter_fn
        self.log_modified_params_only = log_modified_params_only
        self.do_not_log_hooks = do_not_log_hooks
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
            names = [config.match_params("*" + difference[0]) for difference in default.compare(config, reduce=True)]
            if any(len(name) > 1 for name in names):
                raise RuntimeError("ERROR : Compared parameter resolved to 2 parameter names.")
            names = [name[0] for name in names]
        else:
            names = config.get_parameter_names(deep=True, no_sub_config=True)

        # Get filters
        filters = list(self.except_params)
        if self.do_not_log_hooks:
            for hooks in config.get_hook().values():
                filters += hooks

        # Perform filtering
        to_return = []
        for name in names:
            if self.only_params is None or any(
                    compare_string_pattern(config.match_params(name)[0], pattern)
                    for pattern in self.only_params):
                if not any(
                        compare_string_pattern(config.match_params(name)[0], pattern) for pattern in filters):
                    to_return.append(name)
        return to_return

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
        params_to_log = {}
        for pattern in self.get_filtered_params(config):
            param_name = config.match_params(pattern)[0]
            params_to_log[pattern] = config.get_pre_post_processing_values().get(param_name, config[param_name])
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

    def log_image(self, name: str, image, step: Optional[int] = None, sub_logger: Optional[str] = None,
                  maximum: Optional[int] = None, maximum_per_step: Optional[int] = None,
                  main_process_only: bool = False) -> None:
        """
        Logs an image using the logger. The image could be a path to a saved image, matplotlib or plotly figure, a
        PIL.Image, or a n*n*3 numpy array.

        :param name: name for the value to be logged
        :param image: image to be logged. Accepted formats are strings (interpreted as paths to saved images),
            matplotlib or plotly figures, PIL images, or n*n*3 numpy arrays
        :param step: step at which the value is logged. If set to None or a negative value, will default to 0 for the
            tensorboard tracker, will default to -1 for the basic tracker and will be logged as a "single value" for the
            clearml tracker. If not provided, will default to the current step of the tracker (0 by default)
        :param sub_logger: if specified, logs to corresponding sub-logger. Can be interpreted as a sub-folder for the
            scalar name most of the time, but in the case of tensorboard will actually use a different summary writer
        :param maximum: maximum number of images to log. The logger stops logging images once this number is reached.
            If None or negative value, no maximum is set.
        :param maximum_per_step: maximum number of images to log per step. The logger stops logging images once this
            number is reached for a given step. If None or negative value, no maximum is set.
        :param main_process_only: do not try to log in pytorch-lightning sub-processes
        """
        step = self._step if isinstance(step, NoValue) else step
        if not main_process_only or not os.getenv('NODE_RANK'):  # do not track in a pytorch-lightning spawned process
            self._warn_if_no_logs()
            self.loggers.log_image(name=name, image=image, step=step, sub_logger=sub_logger, maximum=maximum,
                                   maximum_per_step=maximum_per_step)

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
