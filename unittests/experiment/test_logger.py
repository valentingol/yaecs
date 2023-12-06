import os
from shutil import rmtree

from .test_project_config.config import UnifiedSegmentationConfig
from .utils import comparison_strings
from yaecs import Experiment


def compare_file_content_to_string(file_path, string, skip_file_first_line=False):
    with open(file_path, "r") as f:
        lines = f.readlines()
    if skip_file_first_line:
        lines = lines[1:]
    assert "".join(lines) == string


def main(config, tracker):
    print(config.details())
    for i in range(10):
        with tracker.measure_time("tracking time"):
            tracker.log_scalar("scalar", i, sub_logger="train")
            tracker.log_scalar("scalar", i+2, sub_logger="test")
        tracker.step()


def test_config_project():
    """ Tests loading a complex config from a sample project. """
    config = UnifiedSegmentationConfig.build_from_argv(
        fallback=["unittests/experiment/test_project_config/experiments/s",
                  "unittests/experiment/test_project_config/experiments/variations"]
    )
    Experiment(config, main).run(run_description="description")
    compare_file_content_to_string(os.path.join(config.b, "f_var_2", "comments.txt"),
                                   comparison_strings["comment"])
    compare_file_content_to_string(os.path.join(config.b, "f_var_2", "config.yaml"),
                                   comparison_strings["config"], True)
    compare_file_content_to_string(os.path.join(config.b, "f_var_2", "config_hierarchy.yaml"),
                                   comparison_strings["hierarchy"])
    # Delete temporary folder
    rmtree("./tmp")
