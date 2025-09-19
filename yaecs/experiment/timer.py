""" This module contains classes to track and manage time durations. """

import logging
import time
from typing import Dict, List, Optional, Tuple, Union

from ..yaecs_utils import compare_string_pattern

YAECS_LOGGER = logging.getLogger(__name__)


class WildCardDict(dict):
    """ This class is a dict where getitem also supports None, lists of items and wildcards ('*'). """
    def __getitem__(self, item: Union[None, str, List[str]]):
        if item is None:
            return self
        if isinstance(item, str) and "*" not in item:
            return super().__getitem__(item)
        if isinstance(item, str):
            return WildCardDict({key: super().__getitem__(key) for key in self.keys()
                                 if compare_string_pattern(key, item)})
        return [self.__getitem__(pattern) for pattern in item]


class Timer:
    """ This class is a timer. It has a name to know what it records, and start and stop times. """
    def __init__(self, name: str = "MyTimer", verbose: Optional[int] = 1, start: bool = False,
                 step: Optional[int] = None, start_time: Optional[float] = None):
        """
        Creates a timer.

        :param name: name of the timer
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail
        :param start: whether to start the timer immediately
        :param step: starting step if start is True (if None, assumes step=0, timings are averages over elapsed steps)
        :param start_time: optional time to start the timer at if start is True (if None, uses current time)
        """
        current_time = time.time() if start_time is None else start_time
        if "*" in name:
            raise ValueError(f"Invalid name for Timer : '{name}'."
                             "The special character '*' cannot be used in Timer names.")
        self.name: str = name
        self.start_times: List[Tuple[Union[float, int]]] = []
        self.stop_times: List[Tuple[Union[float, int]]] = []
        self.verbose: int = 1 if verbose is None else verbose
        if start:
            self.start(step=step, start_time=current_time)

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
    def steps(self) -> List[int]:
        """ Returns the steps on which the timer was recorded. """
        steps = set()
        for i in self.timings:
            for j in range(self.start_times[i][1], self.stop_times[i][1] + 1):
                steps.add(j)
        return sorted(steps)

    @property
    def timings(self) -> List[int]:
        """ Returns the timings recorded by the timer. """
        return list(range(len(self.stop_times)))

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

    def get(self, which: Union[int, str] = "last", step_aggregation: str = "average",
            current_step: Optional[int] = None) -> Optional[float]:
        """
        Gets a specified recorded timing (the last one by default). A recorded timing needs a start and a stop.

        :param which: which timing to get. Can be an int (index of the timing in the list of recorded timings), or
            'last' (last recorded timing), 'first' (first recorded timing), 'average' (average of all recorded timings),
            'total' (sum of all recorded timings) or 'current' (current timing)
        :param step_aggregation: whether to return each timing as an average over the steps it was recorded on or as a
            total. Can be 'average' or 'total'
        :param current_step: current step used to compute the current timing if which is 'current'
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

        # When which is "current", return the current timing as though the timer was stopped at current_time
        if which == "current":
            if self.running:
                return _aggregate(current_time - self.start_times[-1][0],
                                  self.get_number_of_steps("current", current_step=current_step))
            return None

        if self.empty:
            return 0 if which == "total" else None

        # When which is "average", behave differently depending on step_aggregation
        if which == "average":
            if step_aggregation == "average":
                # If step_aggregation is "average", return the average of recorded steps
                return sum(self.get_at_step(i) for i in self.steps)/len(self.steps)
            # If step_aggregation is "total", return the average of recorded timing
            return sum(self.get(which=i, step_aggregation="total") for i in self.timings)/len(self.timings)

        # When which is "total", always return the total recorded duration regardless of step_aggregation
        if which == "total":
            return sum(self.get(which=i, step_aggregation="total") for i in self.timings)

        # When which is an int, return the timing at the given index
        return _aggregate(self.stop_times[which][0] - self.start_times[which][0], self.get_number_of_steps(which))

    def get_at_step(self, step: Optional[Union[int, str]] = None) -> Optional[float]:
        """
        Gets the duration of given step, or None if given step was not recorded. Similar to 'get' except it takes steps
        instead of timing indices. Also accepts 'last' and 'first' as steps.

        :param step: if None last step, else step to get
        :return: the duration if it was recorded, otherwise None
        """
        if step == "first":
            step = self.start_times[0][1]
        if step == "last":
            step = self.stop_times[-1][1]
        if step not in self.steps:
            return None
        step_duration = 0
        for timing in self.timings:
            if self.start_times[timing][1] <= step <= self.stop_times[timing][1]:
                step_duration += self.get(which=timing, step_aggregation="average")
        return step_duration

    def get_number_of_steps(self, which: Union[int, str] = "last", current_step: Optional[int] = None) -> Optional[int]:
        """
        Gets the number of steps of a specified recorded timing (the last one by default).

        :param which: which timing to get. Can be an int (index of the timing in the list of recorded timings), or
            'last' (last recorded timing), 'first' (first recorded timing), 'average' (average of all recorded timings),
            'total' (sum of all recorded timings) or 'current' (current timing)
        :param current_step: current step used to compute the current timing if which is 'current'
        :return: the number of steps
        """
        which = self._process_which(which, possible_strings=["last", "first", "average", "total", "current"])
        if which == "current":
            if not self.running:
                return None
            if current_step is None:
                return 1
            return 1 + current_step - self.start_times[-1][1]
        if self.empty:
            return 0 if which == "total" else None
        if which in ["average", "total"]:
            return self.stop_times[-1][1] - self.start_times[0][1]
        return 1 + self.stop_times[which][1] - self.start_times[which][1]

    def render(self, which: Union[int, str] = "current", step_aggregation: str = "average",
               current_step: Optional[int] = None, verbose: Optional[int] = None) -> str:
        """
        Renders a string to display all or part of the timer's internal state.

        :param which: which timing to get. Can be an int (index of the timing in the list of recorded timings), or
            'current' (current timing), 'last' (last recorded timing), 'first' (first recorded timing), 'average'
            (average of all recorded timings), 'total' (sum of all recorded timings) or 'all' (all recorded timings)
        :param step_aggregation: whether to return each timing as an average over the steps it was recorded on or as a
            total. Can be 'average' or 'total'
        :param current_step: current step used to compute the current timing if which is 'current'
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail
        :raises ValueError: if verbose is not in [0, 1, 2]
        :return: the rendered string
        """
        def _render_duration(which, step_aggregation, current_step, verbose):
            rendered = ""
            duration = self.get(which=which, step_aggregation=step_aggregation, current_step=current_step)
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
            duration = _render_duration(which, step_aggregation, current_step, verbose)
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
                    rendered_string += " ;\n - ".join([_render_duration(i, step_aggregation, current_step, verbose)
                                                       for i in range(len(self.stop_times))])
                    rendered_string += ".\n"
                else:
                    rendered_string += " ; ".join([_render_duration(i, step_aggregation, current_step, verbose)
                                                  for i in range(len(self.stop_times))])

        # Set footer
        if verbose == 2:
            rendered_string += "-" * header_size
        if verbose == 1:
            rendered_string += "."
        if verbose == 0:
            rendered_string += ")"

        return rendered_string

    def reset(self) -> None:
        """ Resets the timer, removing all recorded timings. """
        self.start_times = []
        self.stop_times = []

    def start(self, step: Optional[int] = None, start_time: Optional[float] = None) -> float:
        """
        Automatically stops any previously started timer, and starts a new one.

        :param step: starting step (if none, assumes step=last stop step, timings are averages over the elapsed steps)
        :param start_time: optional time to start the timer at (if None, uses current time)
        :raises ValueError: if step is less than the previous stopping step
        :return: the starting timestamp
        """
        current_time = time.time() if start_time is None else start_time
        if self.stop_times and current_time < self.stop_times[-1][0]:
            raise ValueError(f"Invalid value for 'time' : {current_time}. Must be later than the last stopping time.")
        self.stop(step=step, stop_time=current_time)
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

    def stop(self, step: Optional[int] = None, stop_time: Optional[float] = None) -> Optional[float]:
        """
        Stops any previously started timer, or does nothing if no timer is running.

        :param step: starting step (if none assumes step=starting step + 1, timings are averages over the elapsed steps)
        :param stop_time: optional time to stop the timer at (if None, uses current time)
        :raises ValueError: if step is less than or equal to the previous starting step
        :return: the duration of the timer
        """
        current_time = time.time() if stop_time is None else stop_time
        if not self.running:
            return None
        if current_time < self.start_times[-1][0]:
            raise ValueError(f"Invalid value for 'time' : {current_time}. Must be later than the starting time.")
        previous_step = self.start_times[-1][1]
        step = previous_step if step is None else step
        if step < previous_step:
            raise ValueError(f"Invalid value for 'step' : {step}. Must be greater than the previous starting step.")
        self.stop_times.append((current_time, step))
        ellapsed = current_time - self.start_times[-1][0]
        if self.verbose == 2:
            YAECS_LOGGER.info(f"Timer '{self.name}' stopped at step {step} : ellapsed time "
                              f"{format_duration(ellapsed)} (on average "
                              f"{format_duration(ellapsed/self.get_number_of_steps('last'))} per step).")
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
            which = self.timings[-1]
        elif which == "first":
            which = self.timings[0]
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

    def __getitem__(self, item: Union[int, str]) -> WildCardDict:
        item = self._process_which(item)
        if item == "current":
            return WildCardDict({name: timer.get("current") for name, timer in self.timers.items()})
        if item == "average":
            return WildCardDict({name: timer.get("average", step_aggregation="average")
                                 for name, timer in self.timers.items()})
        if item == "total":
            return WildCardDict({name: timer.get("total") for name, timer in self.timers.items()})
        return WildCardDict({name: timer.get_at_step(item) for name, timer in self.timers.items()})

    @property
    def first_step(self) -> int:
        """ Gets the first step of the timer manager (assuming it is the first step of all its timers). """
        if not self.steps:
            return 0
        return min(self.steps)

    @property
    def last_step(self) -> int:
        """ Gets the last or current step of the timer manager (assuming it is the latest step of all its timers). """
        if not self.steps:
            return 0
        return max(self.steps)

    @property
    def steps(self) -> List[int]:
        """ Gets the sorted steps of the timer manager (ie, the union of the steps of all its timers). """
        return sorted(set(step for timer in self.timers.values() for step in timer.steps))

    def get_timer_names(self, timer: Union[None, str, List[str]] = None) -> List[str]:
        """
        Returns the list of existing timer names corresponding to given name(s). Accepts names with wildcards ('*'). If
        no timer name is matched, sends a warning.

        :param timer: if None (default), returns the names of all timers. Otherwise, returns the names of all timers
            matching the given pattern or at least one of the given patterns
        :return: the list of matched timer names
        """
        matches = []
        all_names = list(self.timers.keys())
        if timer is None:
            return all_names
        if isinstance(timer, str):
            timer = [timer]
        for name in all_names:
            if any(compare_string_pattern(name, pattern) for pattern in timer):
                matches.append(name)
        if not matches:
            YAECS_LOGGER.warning(f"WARNING : No existing timer for patterns '{timer}'.")
        return matches

    def render(self, which_step: Union[int, str] = "last", which_timer: Union[None, str, List[str]] = None,
               slower_than: Optional[float] = None, verbose: Optional[int] = None) -> str:
        """
        Renders a string to display some properties of the timers.

        :param which_step: which timing to get from the timers. Can be an int (index of the step), or 'current'
            (currently running timers), 'last' (last recorded step), 'first' (first recorded step),
            'average' (average of all recorded steps) or 'total' (sum of all recorded steps)
        :param which_timer: which timers to render. Can be None (by default, means all of them), or a timer name or list
            thereof which may contain wildcards ('*')
        :param slower_than: if not None, only renders timers whose duration is greater than this value (in seconds)
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail. If None, uses each timer's verbose
        :return: the rendered string
        """
        rendered_string = ""
        which_step = self._process_which(which_step)
        which_timer = self.get_timer_names(timer=which_timer)
        durations = {name: duration for name, duration in self[which_step].items()
                     if name in which_timer and (slower_than is None or
                                                 (duration is not None and duration > slower_than))}
        verbose = self.verbose if verbose is None else verbose

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
            rendered_string += f"\n---- Reporting on {len(self.timers)} timers {which_string}----\n"
            header_size = len(rendered_string)
        if verbose == 1:
            rendered_string += f"\n{len(self.timers)} timers {which_string}: \n"
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
                if name == list(durations.keys())[-1]:
                    rendered_string = rendered_string[:-3]

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

    def reset(self) -> None:
        """ Resets the manager, deleting all timers. """
        self.timers = {}

    def start(self, name: Union[None, str, List[str]] = "MyTimer", step: Optional[int] = None,
              start_time: Optional[float] = None, verbose: Optional[int] = None) -> None:
        """
        Starts a timer.

        :param name: name or list of names of the timers to start, accepts wildcards ('*'). If None, starts all existing
            timers. For names containing a wildcard, starts all existing matching timers.
        :param step: starting step (if None, assumes step=last stop step, timings are averages over the elapsed steps)
        :param start_time: optional time to start the timer at (if None, uses current time)
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail
        """
        current_time = time.time() if start_time is None else start_time
        if isinstance(name, str):
            name = [name]
        to_start = [] if name is None else [n for n in name if "*" not in n]
        if name is None or any("*" in n for n in name):
            to_start += [n for n in self.get_timer_names(name) if n not in to_start]
        for timer_name in to_start:
            try:
                with TemporaryVerbose(self.timers[timer_name], verbose):
                    self.timers[timer_name].start(step=step, start_time=current_time)
            except KeyError:
                self.timers[timer_name] = Timer(name=timer_name, start=True, step=step, start_time=current_time,
                                                verbose=verbose)

    def stop(self, name: Union[None, str, List[str]] = "MyTimer", step: Optional[int] = None,
             stop_time: Optional[float] = None, verbose: Optional[int] = None) -> Union[None, float, List[float]]:
        """
        Stops a timer.

        :param name: name of the timer or list of timers to stop, accepts wildcards ('*'). None to stop all timers.
        :param step: starting step (if None, assumes step=start step, timings are averages over the elapsed steps)
        :param stop_time: optional time to stop the timer at (if None, uses current time)
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail
        :return: the duration of the timer if it was running, otherwise None
        """
        current_time = time.time() if stop_time is None else stop_time
        names = self.get_timer_names(name)
        to_return = []
        for timer_name in names:
            with TemporaryVerbose(self.timers[timer_name], verbose):
                to_return.append(self.timers[timer_name].stop(step=step, stop_time=current_time))
        if not to_return:
            return None if (isinstance(name, str) and "*" not in name) else []
        return to_return[0] if (isinstance(name, str) and "*" not in name) else to_return

    def update(self, start: Union[None, str, List[str]] = None, stop: Union[None, str, List[str]] = None,
               step: Optional[int] = None, update_time: Optional[float] = None,
               verbose: Optional[int] = None) -> List[Optional[float]]:
        """
        Automatically starts and stops timers.

        :param start: names of the timers to start, accepts wildcards ('*')
        :param stop: names of the timers to stop, accepts wildcards ('*')
        :param step: starting step (if None, assumes step=last stop step, timings are averages over the elapsed steps)
        :param update_time: optional time to update the timers at (if None, uses current time)
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail
        :return: the durations of the stopped timers if any
        """
        current_time = time.time() if update_time is None else update_time
        if start is None:
            start = []
        if isinstance(start, str):
            start = [start]
        if stop is None:
            stop = []
        if isinstance(stop, str):
            stop = [stop]
        timings = [self.stop(name=name, step=step, stop_time=current_time, verbose=verbose) for name in stop]
        for name in start:
            self.start(name=name, step=step, start_time=current_time, verbose=verbose)
        return timings

    def _process_which(self, which: Union[int, str]) -> Union[int, str]:
        """
        Processes 'which' arguments.

        :raises ValueError: if which is not an int or in ['current', 'last', 'first', 'average', 'total']
        :raises IndexError: if which is an int and is out of range
        :return: the processed which
        """
        if isinstance(which, int) and which > self.last_step:
            raise IndexError(f"Unknown step {which} : the last recorded timing in on step {self.last_step}.")
        possible_strings = ["current", "last", "first", "average", "total"]
        if not isinstance(which, int) and which not in possible_strings:
            raise ValueError(f"Invalid value for 'which' : {which}. Can be an int or in {possible_strings}.")
        if which == "last":
            which = self.last_step
        elif which == "first":
            which = self.first_step
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


class TimeInContext:
    """ This Context starts a Timer in given TimerManager at the start of the context and stops it at the end. """
    def __init__(self, timer_manager: TimerManager, name: str = "MyTimer", step: Optional[int] = None,
                 verbose: Optional[int] = None):
        """
        Creates a context to start a timer in a timer manager.

        :param timer_manager: timer manager to start the timer in
        :param name: name of the timer
        :param step: starting step (if None, assumes step=last stop step, timings are averages over the elapsed steps)
        :param verbose: verbosity level. 0 is minimal, 1 is normal, 2 is high detail
        """
        self.timer_manager: TimerManager = timer_manager
        self.name: str = name
        self.step: Optional[int] = step
        self.verbose: Optional[int] = verbose

    def __enter__(self) -> None:
        """ Starts the timer in the timer manager. """
        self.timer_manager.start(name=self.name, step=self.step, verbose=self.verbose)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """ Stops the timer in the timer manager. """
        self.timer_manager.stop(name=self.name, step=self.step, verbose=self.verbose)


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
