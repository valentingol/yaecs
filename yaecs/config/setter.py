""" This file implements a Setter class that is used to process and set parameters. It handles checking types based on
type hints, pre-processing, and post-processing. It can store functions and strings referring to methods, in which case
a method container should be passed to resolve those methods. """
from collections.abc import Iterable
import logging
from numbers import Real
from typing import Any, Callable, Dict, List, Optional, Union

from ..yaecs_utils import (Priority, ProcessingFunction, ProcessingFunctions, ProcessingOrder, TypeHint, UpdateState,
                           check_type, compare_string_pattern, is_type_valid, parse_type)

YAECS_LOGGER = logging.getLogger("yaecs")


class Setter:
    """ Processes parameters to set them in a container. Handles type checking based on type hints, pre-processing, and
    post-processing. Can store functions and strings referring to methods, in which case a method container should be
    passed to resolve those methods. """

    def __init__(self, registered_methods: dict, do_not_pre_process: bool = False, do_not_post_process: bool = False,
                 default_order: ProcessingOrder = Priority.INDIFFERENT, verbose: bool = True):
        """
        Initializes the ParamProcessor object.

        :param registered_methods: dictionary of registered methods and their metadata
        :param do_not_pre_process: whether to skip pre-processing
        :param do_not_post_process: whether to skip post-processing
        :param default_order: default order to use if no order is specified for a processor
        :param verbose: whether to print verbose messages
        """
        self.registered_methods: dict = registered_methods
        self.default_order: ProcessingOrder = default_order
        self.verbose: bool = verbose
        self.processes: List[str] = ([] if do_not_pre_process else ["pre"]) + ([] if do_not_post_process else ["post"])
        self.processors: Dict[str, List['Processor']] = {
            "pre": [],
            "post": [],
        }

    def __call__(self, names: Dict[str, str], values: Dict[str, Any], processing_type: str, container: object,
                 only_set_processed_parameters: bool = False) -> None:
        """
        Processes a parameter based on the processing type.

        :param parameters: parameters to process with names as keys
        :param processing_type: type of processing to perform
        :param container: object containing methods to resolve processors passed as strings, and where to set the values
        :param only_set_processed_parameters: whether to only set the parameters for which at least one processor
        applied
        :return: processed value
        """
        if processing_type not in self.processors:
            raise ValueError(f"Unknown processing_type : '{processing_type}'. "
                             f"Valid types are {list(self.processors.keys())}.")

        processed = []
        if processing_type in self.processes:
            processors = [processor for processor in self.processors[processing_type] if processor.applies(values)]
            processors.sort(key=lambda processor: processor.order)
            processors = self._resolve_type_hints(processors)

            processed_values = dict(values)
            for processor in processors:
                for name, value in processed_values.items():
                    if processor.applies(name):
                        with UpdateState(f"processing;{container.get_name()};arg0={name}", container):
                            processed_values[name] = processor(name, value, container=container)
                        self._set_value(names[name], processed_values[name], container)
                        if name not in processed:
                            processed.append(name)

        if not only_set_processed_parameters:
            for name, value in values.items():
                if name not in processed:
                    self._set_value(names[name], value, container)

        if processing_type == "post" and processed and self.verbose:
            YAECS_LOGGER.info(f"Performed post-processing for modified parameters {processed}.")
        if processing_type == "pre":
            for name, value in values.items():
                if not is_type_valid(values[name], container.__class__):
                    raise RuntimeError(f"ERROR while pre-processing param '{name}' : pre-processing functions that "
                                       "change the type of a param to a non-native YAML type are forbidden because "
                                       "they cannot be saved. Please use a parameter post-processing instead.")

    def add_type_hint(self, type_hint: str, pattern: str, source: Optional[str] = None,
                      no_duplicates: bool = False) -> None:
        """
        Adds a type hint.

        :param type_hint: type hint to add
        :param pattern: pattern that the parameter name must match to be checked
        :param source: if provided, information about the source that added the processor
        :param no_duplicates: whether to check for duplicates before adding
        """
        new_processor = Processor(
            processor=type_hint,
            pattern=pattern,
            is_type_check=True,
            source=source,
        )
        if not no_duplicates or new_processor not in self.processors["pre"]:
            self.processors["pre"].append(new_processor)

    def add_processor(self, processor: ProcessingFunctions, pattern: str, processing_type: Optional[str] = None,
                      order: Optional[ProcessingOrder] = None, source: Optional[str] = None,
                      no_duplicates: bool = False, container: Optional[object] = None) -> None:
        """
        Adds a processor.

        :param processor: processing function
        :param pattern: pattern that the parameter name must match to be processed
        :param processing_type: type of processing to add the processor to
        :param order: order of the processing function
        :param source: if provided, information about the source that added the processor
        :param no_duplicates: whether to check for duplicates before adding
        :param container: if passed, callables passed are stored as strings if they are methods of the container
        """
        # Recover the processor's metadata
        metadata = None
        if isinstance(processor, str):
            if processor in self.registered_methods:
                metadata = self.registered_methods[processor]
            elif container is not None and processor in dir(container):
                candidate = getattr(container, processor)
                if hasattr(candidate, "yaecs_metadata"):
                    metadata = candidate.yaecs_metadata
            else:
                for data in self.registered_methods.values():
                    if "name" in data and data["name"] == processor:
                        metadata = data
                        break
        else:
            metadata = getattr(processor, "yaecs_metadata", None)

        # If the processing type is not provided, infer it from the metadata
        if processing_type is None and (metadata is None or "processing_type" not in metadata):
            source_message = "" if source is None else f" (added from {source})"
            raise ValueError("Processing type was not provided and could not be inferred from metadata for processor "
                             f"'{processor}'{source_message} defined for pattern '{pattern}'.")
        if processing_type is None:
            processing_type = metadata["processing_type"]

        # If the processor is a method of the container, store it as a string
        if container is not None and isinstance(processor, Callable):
            if hasattr(processor, "yaecs_metadata"):
                name = processor.yaecs_metadata.get("name", getattr(processor, "__name__", "unknown_function"))
            else:
                name = getattr(processor, "__name__", "unknown_function")
            if name in dir(container):
                candidate = getattr(container, name)
                processor_metadata = getattr(processor, "yaecs_metadata", {})
                candidate_metadata = getattr(candidate, "yaecs_metadata", {})
                if isinstance(candidate, Callable) and processor_metadata == candidate_metadata:
                    processor = name
                    processor_metadata["name"] = name
                    self.registered_methods[name] = processor_metadata
                    metadata = processor_metadata

        # Create the new processor
        new_processor = Processor(
            processor=processor,
            pattern=pattern,
            order=order,
            default_order=self.default_order,
            is_type_check=False,
            source=source,
            metadata=metadata,
        )

        # Add the new processor
        if not no_duplicates or new_processor not in self.processors[processing_type]:
            self.processors[processing_type].append(new_processor)
            if metadata and "input_type" in metadata:
                self.add_type_hint(metadata["input_type"], pattern, source=f"method[{processor}]")
            if new_processor.metadata is not None and "processing_type" in new_processor.metadata:
                advised_type = new_processor.metadata["processing_type"]
                if advised_type != processing_type:
                    YAECS_LOGGER.warning(f"WARNING : processor '{new_processor.name}' is recommended to use as "
                                         f"{advised_type}-processing function, but was declared as "
                                         f"{processing_type}-processing function.")

    def bulk_add_type_hints(self, type_hints: Dict[str, str], source: Optional[str] = None,
                            no_duplicates: bool = False) -> None:
        """
        Adds multiple type hints at once.

        :param type_hints: dictionary of type hints to add
        :param source: if provided, information about the source that added the type hints
        :param no_duplicates: whether to check for duplicates before adding
        """
        for pattern, type_hint in type_hints.items():
            self.add_type_hint(type_hint=type_hint, pattern=pattern, source=source, no_duplicates=no_duplicates)

    def bulk_add_processors(self, processors: Dict[str, ProcessingFunctions], processing_type: Optional[str] = None,
                            source: Optional[str] = None, no_duplicates: bool = False,
                            container: Optional[object] = None) -> None:
        """
        Adds multiple processors at once.

        :param processors: dictionary of processors to add
        :param processing_type: type of processing to add the processors to. If None, must be inferrable from metadata
        :param source: if provided, information about the source that added the processors
        :param no_duplicates: whether to check for duplicates before adding
        :param container: if passed, callables passed are stored as strings if they are methods of the container
        """
        for pattern, processor in processors.items():
            if not isinstance(processor, (Callable, Iterable)):
                source_message = "" if source is None else f" (added from {source})"
                type_message = "" if processing_type is None else f"{processing_type}-"
                raise TypeError(f"Invalid {type_message}processing functions{source_message} defined for pattern "
                                f"'{pattern}' : the function should be declared as either a function or an iterable of "
                                "functions, optionally containing one order value.")

            order = None
            if isinstance(processor, Iterable) and not isinstance(processor, str):
                if any(not isinstance(element, (Callable, str, Real, Priority)) for element in processor):
                    source_message = "" if source is None else f" (added from {source})"
                    type_message = "" if processing_type is None else f"{processing_type}-"
                    raise TypeError(f"Invalid {type_message}processing functions{source_message} defined for "
                                    f"pattern '{pattern}' : if function is declared as iterable, only functions and "
                                    "one order value can be provided.")
                order = [o for o in processor if isinstance(o, (Real, Priority))]
                if len(order) > 1:
                    source_message = "" if source is None else f" (added from {source})"
                    type_message = "" if processing_type is None else f"{processing_type}-"
                    raise ValueError(f"Ambiguous order for {type_message}processing functions{source_message} "
                                     f"defined for pattern '{pattern}' : multiple orders defined ({order}).")
                processor = [p for p in processor if isinstance(p, (Callable, str))]
                order = order[0] if order else None

            else:
                processor = [processor]

            for p in processor:
                self.add_processor(processor=p, pattern=pattern, processing_type=processing_type, order=order,
                                   source=source, no_duplicates=no_duplicates, container=container)

    def set_post_processing(self, value: bool = True):
        """
        Sets whether to post-process.

        :param value: whether to post-process
        """
        self._set_processing(value, "post")

    def set_pre_processing(self, value: bool = True):
        """
        Sets whether to pre-process.

        :param value: whether to pre-process
        """
        self._set_processing(value, "pre")

    def _set_processing(self, value: bool, processing_type: str):
        """
        Sets whether to process for a given processing type.

        :param value: whether to process
        :param processing_type: type of processing to set
        """
        if value and processing_type not in self.processes:
            self.processes.append(processing_type)
        elif not value and processing_type in self.processes:
            self.processes.remove(processing_type)

    def _set_value(self, name, value, container) -> None:
        """
        Sets the value of a parameter.

        :param name: name of the parameter
        :param value: value to set
        :param container: object containing the parameter
        """
        sub_container = ".".join(name.split(".")[:-1])
        param_name = name.split(".")[-1]
        object.__setattr__((container.get_main_config()[sub_container] if sub_container else container),
                           param_name, value)

    def _resolve_type_hints(self, processors: List['Processor']) -> List['Processor']:
        """
        Remove type hints from the processors if they are erroneous.

        :param processors: processors to resolve
        :return: resolved processors
        """
        type_hints = [processor for processor in processors if processor.is_type_check]
        if not type_hints:
            return processors

        valid_auto_type_hint = []
        for type_hint in type_hints:
            source = "" if type_hint.source is None else type_hint.source
            is_auto_type_hint = source.startswith("method[") and source.endswith("]")
            if not is_auto_type_hint:
                return [type_hint] + processors[len(type_hints):]
            if source[len("method["):len("]")] == processors[0].processor:
                valid_auto_type_hint = [type_hint]

        return valid_auto_type_hint + processors[len(type_hints):]


class Processor:
    """ Class used to store a processing function. """
    MIN_ORDER = -1000000

    def __init__(self, processor: ProcessingFunction, pattern: str, order: Optional[ProcessingOrder] = None,
                 default_order: ProcessingOrder = Priority.INDIFFERENT, is_type_check: bool = False,
                 source: Optional[str] = None, metadata: Optional[dict] = None):
        """
        Initializes the Processor object.

        :param processor: processing function
        :param pattern: pattern that the parameter name must match to be processed
        :param order: order of the processing function
        :param default_order: order to use if no order is specified
        :param is_type_check: whether the function is a type to be checked
        :param source: if type check was added automatically, which method it was added from
        :param metadata: dictionary of metadata about the processor
        """
        self.pattern: str = pattern
        self.is_type_check: bool = is_type_check
        self.source: Optional[str] = source
        self.metadata: dict = {} if metadata is None else metadata
        if not isinstance(processor, str) and hasattr(processor, "yaecs_metadata"):
            self.metadata.update(processor.yaecs_metadata)
        self.name = self._resolve_name(processor)
        self.processor: Union[ProcessingFunction, TypeHint] = parse_type(processor) if self.is_type_check else processor
        self.order: ProcessingOrder = self._resolve_order(order, default_order)

    def __call__(self, name: str, old_value: Any, container: Optional[object] = None) -> Any:
        """
        Calls the processing function.

        :param name: name of the parameter
        :param old_value: argument to pass to the function
        :param container: object containing methods to resolve processors passed as strings
        :return: return value of the function
        """
        if not self.applies(name):
            return old_value
        function = self._resolve(container, name)
        try:
            return function(old_value)
        except Exception:
            YAECS_LOGGER.error(f"ERROR while processing param '{name}'.")
            raise

    def __eq__(self, other: 'Processor') -> bool:
        """
        Checks whether two processors are equal.

        :param other: processor to compare
        :return: whether the processors are equal
        """
        return (self.pattern == other.pattern and self.name == other.name and self.order == other.order
                and self.source == other.source)

    def applies(self, params_or_param_name: Union[Dict[str, Any], str]) -> bool:
        """
        Checks whether the processor applies to the parameter(s).

        :param params_or_param_name: parameter(s) to check
        :return: whether the processor applies
        """
        if isinstance(params_or_param_name, str):
            return compare_string_pattern(params_or_param_name, self.pattern)
        return any(compare_string_pattern(name, self.pattern) for name in params_or_param_name.keys())

    def _resolve(self, container: object, name: str) -> Callable:
        """
        If the processor is a string, this method resolves the string to a method of the container.

        :param container: object containing methods to resolve processors passed as strings
        :return: resolved function
        """
        if self.is_type_check:
            return check_type(self.processor, name)
        if isinstance(self.processor, str):
            if (self.name not in dir(container)
                    or not isinstance(getattr(container, self.name), Callable)):
                source_message = "" if self.source is None else f" (added from {self.source})"
                raise ValueError(f"Method '{self.name}'{source_message} not found in {container}.")
            return getattr(container, self.name)
        return self.processor

    def _resolve_name(self, processor: ProcessingFunction) -> str:
        """
        Resolves the name of the processor.

        :param processor: processor to resolve the name of
        :return: resolved name
        """
        if "name" in self.metadata:
            return self.metadata["name"]
        return processor if isinstance(processor, str) else getattr(processor, "__name__", "unknown_function")

    def _resolve_order(self, order_overwrite: Optional[ProcessingOrder],
                       default_order: ProcessingOrder = Priority.INDIFFERENT) -> ProcessingOrder:
        """
        Resolves the order of the function.

        :param order_overwrite: order to use over all other orders
        :param default_order: default order to use if no order is specified
        :return: resolved order
        """
        if self.is_type_check:
            return self.MIN_ORDER - 1

        order = order_overwrite if order_overwrite is not None else self.metadata.get("order", default_order)
        return max(order, self.MIN_ORDER)
