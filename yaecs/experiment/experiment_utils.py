""" Experiment utility functions. """
from typing import List, Union


def format_mode(mode: Union[str, List[str]]) -> str:
    """ Formats the experiment mode for the purpose of the experiment comment. """
    modes = {
        "TRAINING": ["train", "learn", "fit"],
        "TESTING": ["test", "evaluate", "benchmark"],
        "VALIDATION": ["val"],
        "INFERENCE": ["infer", "predict", "forecast", "apply"],
        "DATA PROCESSING": ["process", "preprocess", "data"],
        "DEBUG": ["debug", "inspect"],
    }
    if isinstance(mode, str):
        mode = [mode]
    formatted = []
    for mode_ in mode:
        matched = f'"{mode_.upper()}"'
        for key, values in modes.items():
            if any(mode_.lower().startswith(value) for value in values):
                matched = key
                break
        formatted.append(matched)
    return ", ".join(formatted)
