""" This module contains classes to track and manage time durations. """

import logging
import time
from typing import Dict, List, Optional, Tuple, Union

YAECS_LOGGER = logging.getLogger(__name__)


class Timer:
    """ This class is a timer. It has a name to know what it records, and start and stop times. """
    def __init__(self, name: str = "MyTimer", verbose: int = 1, start: bool = False, step: Optional[int] = None):
        """
        Creates a timer.

        :param name: name of the timer
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail
        :param start: whether to start the timer immediately
        :param step: starting step if start is True (if None, assumes step=0, timings are averages over elapsed steps)
        """
        self.name: str = name
        self.start_times: List[Tuple[Union[float, int]]] = []
        self.stop_times: List[Tuple[Union[float, int]]] = []
        self.verbose: int = verbose
        if start:
            self.start(step=step)

    def __str__(self) -> str:
        return self.render("current") if self.running else self.render("last")

    def __getitem__(self, item: Union[int, str]) -> Optional[float]:
        return self.get(which=item, step_aggregation="average")

    @property
    def empty(self) -> bool:
        """ Returns whether the timer has completed any run. """
        return len(self.stop_times) == 0

    @property
    def running(self) -> bool:
        """ Returns whether the timer is currently running. """
        return len(self.start_times) > len(self.stop_times)

    @property
    def verbose(self) -> int:
        """ Returns the verbosity level of the timer. """
        return self._verbose

    @verbose.setter
    def verbose(self, verbose: int) -> None:
        """ Sets the verbosity level of the timer. """
        if verbose not in [0, 1, 2]:
            raise ValueError(f"Invalid value for 'verbose' : {verbose}. Can be 0, 1 or 2.")
        self._verbose = verbose

    def get(self, which: Union[int, str] = "last", step_aggregation: str = "average") -> Optional[float]:
        """
        Gets a specified recorded timing (the last one by default). A recorded timing needs a start and a stop.

        :param which: which timing to get. Can be an int (index of the timing in the list of recorded timings), or
            'last' (last recorded timing), 'first' (first recorded timing), 'average' (average of all recorded timings),
            'total' (sum of all recorded timings) or 'current' (current timing)
        :param step_aggregation: whether to return each timing as an average over the steps it was recorded on or as a
            total. Can be 'average' or 'total'
        :raises ValueError: if which is not an int or in ['last', 'first', 'average', 'total']
        :raises IndexError: if which is an int and is out of range
        :return: the timing
        """
        current_time = time.time()

        def _aggregate(value, number_of_steps):
            return value / number_of_steps if step_aggregation == "average" else value
        if step_aggregation not in ["average", "total"]:
            raise ValueError(f"Invalid value for 'step_aggregation' : {step_aggregation}. Can be 'average' or 'total'.")
        which = self._process_which(which, possible_strings=["last", "first", "average", "total", "current"])

        if which == "current":
            return current_time - self.start_times[-1][0] if self.running else None

        if self.empty:
            return 0 if which == "total" else None

        if which == "average":
            step_divider = sum(self.get_number_of_steps(i) for i in range(len(self.stop_times)))
            divider = step_divider if step_aggregation == "total" else len(self.stop_times)
            return sum(_aggregate(self.stop_times[i][0] - self.start_times[i][0], self.get_number_of_steps(i))
                       for i in range(len(self.stop_times))) / divider

        if which == "total":
            return sum(_aggregate(self.stop_times[i][0] - self.start_times[i][0], self.get_number_of_steps(i))
                       for i in range(len(self.stop_times)))

        return _aggregate(self.stop_times[which][0] - self.start_times[which][0], self.get_number_of_steps(which))

    def get_at_step(self, step: Optional[int] = None) -> Optional[float]:
        """
        Gets the duration of given step, or None if given step was not recorded. Similar to 'get' except it takes steps
        instead of timing indices.

        :param step: if None last step, else step to get
        :return: the duration if it was recorded, otherwise None
        """
        index = None
        for i, stop_time in enumerate(self.stop_times):
            if stop_time[1] > step:
                index = i
                break
        if self.start_times[index][1] > step or index is None:
            return None
        return self.get(which=index, step_aggregation="average")

    def get_number_of_steps(self, which: Union[int, str] = "last") -> Optional[int]:
        """
        Gets the number of steps of a specified recorded timing (the last one by default).

        :param which: which timing to get. Can be an int (index of the timing in the list of recorded timings), or
            'last' (last recorded timing), 'first' (first recorded timing), 'average' (average of all recorded timings)
            or 'total' (sum of all recorded timings)
        :return: the number of steps
        """
        which = self._process_which(which, possible_strings=["last", "first", "average", "total"])
        if self.empty:
            return 0 if which == "total" else None
        if which in ["average", "total"]:
            return self.stop_times[-1][1] - self.start_times[0][1]
        return self.stop_times[which][1] - self.start_times[which][1]

    def render(self, which: Union[int, str] = "current", step_aggregation: str = "average",
               verbose: Optional[int] = None) -> str:
        """
        Renders a string to display all or part of the timer's internal state.

        :param which: which timing to get. Can be an int (index of the timing in the list of recorded timings), or
            'current' (current timing), 'last' (last recorded timing), 'first' (first recorded timing), 'average'
            (average of all recorded timings), 'total' (sum of all recorded timings) or 'all' (all recorded timings)
        :param step_aggregation: whether to return each timing as an average over the steps it was recorded on or as a
            total. Can be 'average' or 'total'
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail
        :raises ValueError: if verbose is not in [0, 1, 2]
        :return: the rendered string
        """
        def _render_duration(which, step_aggregation, verbose):
            rendered = ""
            duration = self.get(which=which, step_aggregation=step_aggregation)
            if duration is None:
                if verbose == 2:
                    rendered += "no timing recorded so far"
                if verbose == 1:
                    rendered += "none"
                if verbose == 0:
                    rendered += "-"
            else:
                duration = format_duration(duration, human_readable=bool(verbose))
                number_of_steps = self.get_number_of_steps(which)
                if verbose == 2:
                    timing_name = f"{which} timing" if isinstance(which, str) else f"timing {which}"
                    step_operation = "averaged" if step_aggregation == "average" else "accumulated"
                    step_rendering = f" ({step_operation} over {number_of_steps} steps)" if number_of_steps > 1 else ""
                    rendered += f"{timing_name} : {duration}{step_rendering}"
                if verbose == 1:
                    step_operation = "/" if step_aggregation == "average" else "in"
                    step_rendering = f" ({step_operation} {number_of_steps} steps)" if number_of_steps > 1 else ""
                    rendered += f"{duration}{step_rendering}"
                if verbose == 0:
                    rendered += f"{duration}"
            return rendered
        current_time = time.time()
        verbose = self.verbose if verbose is None else verbose
        if verbose not in [0, 1, 2]:
            raise ValueError(f"Invalid value for 'verbose' : {verbose}. Can be 0, 1 or 2.")
        which_tmp = self._process_which(which, possible_strings=["current", "last", "first", "average", "total", "all"])
        which = which if which in ["last", "first"] else which_tmp
        rendered_string = ""

        # Set header
        if verbose == 2:
            rendered_string += f"---- '{self.name}' timer ----\n"
            header_size = len(rendered_string)
        if verbose == 1:
            rendered_string += f"'{self.name}' : "
        if verbose == 0:
            rendered_string += f"{self.name}("

        # Set summary
        if verbose == 2:
            steps = sum(self.stop_times[i][1] - self.start_times[i][1] for i in range(len(self.stop_times)))
            rendered_string += f"Overall {len(self.stop_times)} recorded timings totalling {steps} steps.\n"

        # Set body
        if which == "current":
            if self.running:
                duration = format_duration(current_time - self.start_times[-1][0], human_readable=bool(verbose))
                if verbose == 2:
                    rendered_string += f"Currently running for {duration}.\n"
                if verbose == 1:
                    rendered_string += f"running for {duration}"
            else:
                duration = "-"
                if verbose == 2:
                    rendered_string += "Currently not running.\n"
                if verbose == 1:
                    rendered_string += "not running"
            if verbose == 0:
                rendered_string += f"{duration}"
        elif which != "all":
            duration = _render_duration(which, step_aggregation, verbose)
            if verbose == 2:
                rendered_string += f"{duration.capitalize()}.\n"
            else:
                rendered_string += duration
        else:
            if self.empty:
                if verbose == 2:
                    rendered_string += "No timing recorded so far.\n"
                if verbose == 1:
                    rendered_string += "none"
                if verbose == 0:
                    rendered_string += "-"
            else:
                if verbose == 2:
                    rendered_string += "All recorded timings :\n - "
                    rendered_string += " ;\n - ".join([_render_duration(i, step_aggregation, verbose)
                                                       for i in range(len(self.stop_times))])
                    rendered_string += ".\n"
                else:
                    rendered_string += " ; ".join([_render_duration(i, step_aggregation, verbose)
                                                  for i in range(len(self.stop_times))])

        # Set footer
        if verbose == 2:
            rendered_string += "-" * header_size
        if verbose == 1:
            rendered_string += "."
        if verbose == 0:
            rendered_string += ")"

        return rendered_string

    def start(self, step: Optional[int] = None) -> float:
        """
        Automatically stops any previously started timer, and starts a new one.

        :param step: starting step (if none, assumes step=last stop step, timings are averages over the elapsed steps)
        :raises ValueError: if step is less than the previous stopping step
        :return: the starting timestamp
        """
        current_time = time.time()
        self.stop(step=step, _time=current_time)
        previous_step = 0
        if not self.empty:
            previous_step = self.stop_times[-1][1]
        step = previous_step if step is None else step
        if step < previous_step:
            raise ValueError(f"Invalid value for 'step' : {step}. Must be greater than or equal to the previous "
                             "stopping step.")
        self.start_times.append((current_time, step))
        if self.verbose == 2:
            YAECS_LOGGER.info(f"Timer '{self.name}' started at step {step} at time "
                              f"{time.asctime(time.localtime(current_time))}.")
        return current_time

    def stop(self, step: Optional[int] = None, _time: Optional[float] = None) -> Optional[float]:
        """
        Stops any previously started timer, or does nothing if no timer is running.

        :param step: starting step (if none assumes step=starting step + 1, timings are averages over the elapsed steps)
        :raises ValueError: if step is less than or equal to the previous starting step
        :return: the duration of the timer
        """
        current_time = time.time() if _time is None else _time
        if not self.running:
            return None
        previous_step = self.start_times[-1][1]
        step = previous_step + 1 if step is None else step
        if step <= previous_step:
            raise ValueError(f"Invalid value for 'step' : {step}. Must be greater than the previous starting step.")
        self.stop_times.append((current_time, step))
        ellapsed = current_time - self.start_times[-1][0]
        if self.verbose == 2:
            YAECS_LOGGER.info(f"Timer '{self.name}' stopped at step {step} : ellapsed time "
                              f"{format_duration(ellapsed)} (on average "
                              f"{format_duration(ellapsed/(step-previous_step))} per step).")
        return ellapsed

    def _process_which(self, which: Union[int, str], possible_strings: List[str]) -> Union[int, str]:
        """
        Processes 'which' arguments.

        :raises ValueError: if which is not an int or in possible_strings
        :raises IndexError: if which is an int and is out of range
        :return: the processed which
        """
        if isinstance(which, int) and which >= len(self.stop_times):
            raise IndexError(f"Index {which} is out of range for timer {self.name} with {len(self.stop_times)} "
                             "recorded timings.")
        if not isinstance(which, int) and which not in possible_strings:
            raise ValueError(f"Invalid value for 'which' : {which}. Can be an int or in {possible_strings}.")
        if which == "last":
            which = len(self.stop_times) - 1
        elif which == "first":
            which = 0
        return which


class TimerManager:
    """ This class records timings and prints or returns them in a variety of formats. """
    def __init__(self, verbose: Optional[int] = None):
        """
        Creates a timer manager use to start and stop timers, as well as render them.

        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail. If None, set based on local logger
        """
        self.timers: Dict[str, Timer] = {}
        level = YAECS_LOGGER.getEffectiveLevel()
        level_verbose = 0 if level > 30 else 1 if level > 10 else 2
        verbose = level_verbose if verbose is None else verbose
        self.verbose: int = verbose

    def __getitem__(self, item: Union[int, str]) -> Dict[str, Optional[float]]:
        item = self._process_which(item)
        if item == "current":
            return {name: timer.get("current") for name, timer in self.timers.items()}
        if item == "average":
            return {name: timer.get("average", step_aggregation="total") for name, timer in self.timers.items()}
        if item == "total":
            return {name: timer.get("total", step_aggregation="total") for name, timer in self.timers.items()}
        return {name: timer.get_at_step(item) for name, timer in self.timers.items()}

    @property
    def first_step(self) -> int:
        """ Gets the first step of the timer manager (assuming it is the first step of all its timers). """
        return min(timer.start_times[-1][1] for timer in self.timers.values())

    @property
    def last_step(self) -> int:
        """ Gets the last or current step of the timer manager (assuming it is the latest step of all its timers). """
        return max(timer.start_times[-1][1] for timer in self.timers.values())

    def render(self, which_step: Union[int, str] = "current", verbose: Optional[int] = None) -> str:
        """
        Renders a string to display some properties of the timers.

        :param which_step: which timing to get from the timers. Can be an int (index of the step), or 'current'
            (currently running timers), 'last' (last recorded step), 'first' (first recorded step),
            'average' (average of all recorded steps) or 'total' (sum of all recorded steps)
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail. If None, uses each timer's verbose
        :return: the rendered string
        """
        rendered_string = ""
        which_step = self._process_which(which_step)
        durations = self[which_step]

        # Set header
        if which_step == "current":
            which_string = "(currently) "
        elif which_step == "average":
            which_string = f"(averaged over {self.last_step - self.first_step} steps) "
        elif which_step == "total":
            which_string = f"(accumulated over {self.last_step - self.first_step} steps) "
        else:
            which_string = f"(at step {which_step}) "
        if verbose == 2:
            rendered_string += f"---- Reporting on {len(self.timers)} timers {which_string}----\n"
            header_size = len(rendered_string)
        if verbose == 1:
            rendered_string += f"{len(self.timers)} timers {which_string}: \n"
        if verbose == 0:
            rendered_string += "{"

        # Set body
        if not durations:
            if verbose in [1, 2]:
                rendered_string += "No timer set so far.\n"
            if verbose == 0:
                rendered_string += " - "
        for name, duration in durations.items():
            if duration is None:
                continue
            if verbose in [1, 2]:
                rendered_string += f" - {name} : {format_duration(duration)}\n"
            if verbose == 0:
                rendered_string += f"{name}:{format_duration(duration)} ; "

        # Set footer
        if verbose in [1, 2]:
            not_reported = [name for name, duration in durations.items() if duration is None]
            if len(not_reported) > 0:
                reported_string = "running" if which_step == "current" else "recorded "
                reported_string += "so far" if which_step in ["total", "average"] else ""
                reported_string += f"at step {which_step}" if isinstance(which_step, int) else ""
                rendered_string += f"{len(not_reported)} timers not {reported_string} ({', '.join(not_reported)}).\n"
        if verbose == 2:
            rendered_string += "-" * header_size
        if verbose == 0:
            rendered_string += "}"

        return rendered_string

    def start(self, name: str = "MyTimer", step: Optional[int] = None, verbose: Optional[int] = None) -> None:
        """
        Starts a timer.

        :param name: name of the timer
        :param step: starting step (if None, assumes step=last stop step, timings are averages over the elapsed steps)
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail
        """
        try:
            with TemporaryVerbose(self.timers[name], verbose):
                self.timers[name].start(step=step)
        except KeyError:
            self.timers[name] = Timer(name=name, start=True, step=step, verbose=verbose)

    def stop(self, name: str = "MyTimer", step: Optional[int] = None, verbose: Optional[int] = None) -> None:
        """
        Stops a timer.

        :param name: name of the timer
        :param step: starting step (if None, assumes step=start step + 1, timings are averages over the elapsed steps)
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail
        """
        with TemporaryVerbose(self.timers[name], verbose):
            self.timers[name].stop(step=step)

    def _process_which(self, which: Union[int, str]) -> Union[int, str]:
        """
        Processes 'which' arguments.

        :raises ValueError: if which is not an int or in ['current', 'last', 'first', 'average', 'total']
        :raises IndexError: if which is an int and is out of range
        :return: the processed which
        """
        if isinstance(which, int) and which >= len(self.stop_times):
            raise IndexError(f"Index {which} is out of range for timer {self.name} with {len(self.stop_times)} "
                             "recorded timings.")
        possible_strings = ["current", "last", "first", "average", "total"]
        if not isinstance(which, int) and which not in possible_strings:
            raise ValueError(f"Invalid value for 'which' : {which}. Can be an int or in {possible_strings}.")
        if which == "last":
            which = len(self.stop_times) - 1
        elif which == "first":
            which = 0
        return which


class TemporaryVerbose:
    """ Context manager to change the verbosity of a timer. """
    def __init__(self, timer: Timer, verbose: int):
        """
        Creates a context manager to change the verbosity of a timer.

        :param timer: timer to change the verbosity of
        :param verbose: new verbosity level
        """
        self.timer: Timer = timer
        self.verbose: int = verbose
        self.old_verbose: Optional[int] = None

    def __enter__(self) -> None:
        """ Changes the verbosity level of the timer. """
        if self.verbose is not None:
            self.old_verbose = self.timer.verbose
            self.timer.verbose = self.verbose

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """ Resets the verbosity level of the timer. """
        if self.old_verbose is not None:
            self.timer.verbose = self.old_verbose


def format_duration(duration: float, precision: int = 2, human_readable: bool = True) -> str:
    """ Formats a duration in seconds to a string. """
    if not human_readable:
        return f"{duration:.{precision}f}"
    groups = {"w": 604800, "d": 86400, "h": 3600, "m": 60}
    formatted = ""
    for name, seconds in groups.items():
        if duration >= seconds:
            formatted += f"{int(duration // seconds)}{name} "
            duration %= seconds
    return f"{formatted}{duration:.{precision}f}s"
