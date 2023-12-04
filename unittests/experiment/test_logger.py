import os
from shutil import rmtree

from .test_project_config.config import UnifiedSegmentationConfig
from yaecs import Experiment

expected_comment_2 = """[2/2] Variation f_var_1 (variation f_var_2)
Purpose : description"""
expected_hierarchy_2 = """config_hierarchy:
- /home/vac/Documents/Projects/ait-yaecs/unittests/experiment/test_project_config/defaults/default.yaml
- unittests/experiment/test_project_config/experiments/s
- unittests/experiment/test_project_config/experiments/variations
- a_config:
    ts:
      t4:
        fr: b
        use: true
"""
expected_config_2 = """a: false
b: tmp/normal/test
c: Try something
d: v
e: 1
f:
  var_1:
    a_config:
      ts:
        t4:
          use: false
  var_2:
    a_config:
      ts:
        t4:
          use: true
          fr: b
a_config:
  a: true
  t:
    s: 1024
    pp:
      p:
      - t1
      - t2
      - t3
      - t5
      - t4
      sp: {}
  v:
    s:
    - 320
    - 480
    pp:
      p:
      - t1
      - t5
      - t4
      sp:
        t1.t1m: false
        t2.t1m: false
  te:
    s:
    - 320
    - 480
    pp:
      p:
      - t1
      - t5
      - t4
      sp:
        t1.t1m: false
        t2.t1m: false
  ts:
    t1:
      use: true
      t1m: true
    t2:
      use: true
      t1m: true
    t3:
      use: false
      t3_probability: 0.4
      m: 0
    t4:
      use: true
      fr: b
    t5:
      use: true
      nm: 1
a_config_file: a_config.yaml
b_config:
  atc: svb
b_config_file: b_config.yaml
t:
  tf: folder
  tn: 50
v:
  vf: 5
c_config_file: c_config.yaml
d_config_file: unittests/experiment/test_project_config/general/bsc
tracker_config:
  type:
  - basic
  - clearml
  project_name: yaecs_dev_tests
"""


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
    compare_file_content_to_string(os.path.join(config.b, "f_var_2", "comments.txt"), expected_comment_2)
    compare_file_content_to_string(os.path.join(config.b, "f_var_2", "config.yaml"), expected_config_2, True)
    compare_file_content_to_string(os.path.join(config.b, "f_var_2", "config_hierarchy.yaml"), expected_hierarchy_2)
    # Delete temporary folder
    rmtree("./tmp")
