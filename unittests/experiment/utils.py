""" Defines some utility functions and objects for the experiment tests. """


comparison_strings = {
    "comment": """[2/2] VALIDATION run in tmp/normal/test_0/f_var_2 (variation f_var_2) :
Purpose : description""",
    "hierarchy": """config_hierarchy:
- /home/vac/Documents/Projects/ait-yaecs/unittests/experiment/test_project_config/defaults/default.yaml
- unittests/experiment/test_project_config/experiments/s
- unittests/experiment/test_project_config/experiments/variations
- a_config.ts.t4.fr: b
  a_config.ts.t4.use: true
  mode: validation
""",
    "config": """a: false
b: tmp/normal/test
c: Try something
d: v
e: 1
f: !type:dict
  var_1: !type:dict
    a_config.ts.t4.use: false
    mode: training
  var_2: !type:dict
    a_config.ts.t4.use: true
    a_config.ts.t4.fr: b
    mode: validation
mode: validation
a_config_file: a_config.yaml
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
      sp: !type:dict {}
  v:
    s:
    - 320
    - 480
    pp:
      p: &id001
      - t1
      - t5
      - t4
      sp: !type:dict
        t1.t1m: false
        t2.t1m: false
  te:
    s:
    - 320
    - 480
    pp:
      p: *id001
      sp: !type:dict
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
b_config_file: b_config.yaml
b_config:
  atc: svb
c_config_file: c_config.yaml
t:
  tf: folder
  tn: 50
v:
  vf: 5
d_config_file: unittests/experiment/test_project_config/general/bsc
tracker_config: !type:dict
  type:
  - basic
  - clearml
  project_name: yaecs_dev_tests
""",
}
