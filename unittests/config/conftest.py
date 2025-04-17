"""
Reactive Reality Machine Learning Config System - unit tests
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
import os

import pytest

from yaecs.user_utils import make_config


@pytest.fixture
def tmp_file_name(tmpdir):
    index = 1 + max([-1] + [
        int(fil[3:-5]) for fil in os.listdir(tmpdir)
        if fil.startswith('tmp') and fil.endswith('.yaml')
    ])
    filename = tmpdir / f'tmp{index}.yaml'
    yield filename


@pytest.fixture
def yaml_default(tmpdir):
    index = len(os.listdir(tmpdir))
    content = (f"param1: 0.1\n--- !subconfig1\nparam2: 3.0\n---\n"
               f"def_second_path: '{tmpdir / f'default_second{index}.yaml'}'\n"
               "exp_second_path: null")
    with open(tmpdir / f'default{index}.yaml', "w", encoding='utf-8') as fil:
        fil.write(content)
    content = ("--- !subconfig2\nparam3: 20.0\nsubconfig3:\n  "
               "param4: 'string'")
    with open(tmpdir / f'default_second{index}.yaml', "w",
              encoding='utf-8') as fil:
        fil.write(content)
    yield str(tmpdir / f'default{index}.yaml')


@pytest.fixture
def yaml_experiment(tmpdir):
    index = len(os.listdir(tmpdir))
    content = ("subconfig1.param2: 2.0\n\nexp_second_path: \""
               f"experiment_second{index}.yaml\"")
    with open(tmpdir / f'experiment{index}.yaml', "w",
              encoding='utf-8') as fil:
        fil.write(content)
    content = "--- !subconfig2\nparam3: 30.0"
    with open(tmpdir / f'experiment_second{index}.yaml', "w",
              encoding='utf-8') as fil:
        fil.write(content)
    yield str(tmpdir / f'experiment{index}.yaml')


@pytest.fixture
def yaml_default_preproc_default_dot_param(tmpdir):
    content = "param1.param2: 2"
    with open(tmpdir / f'tmp{len(os.listdir(tmpdir))}.yaml', "w",
              encoding='utf-8') as fil:
        fil.write(content)
    yield str(tmpdir / f'tmp{len(os.listdir(tmpdir))-1}.yaml')


@pytest.fixture
def yaml_default_sub_variations(tmpdir):
    content = "param1:\n  var: []"
    with open(tmpdir / f'tmp{len(os.listdir(tmpdir))}.yaml', "w",
              encoding='utf-8') as fil:
        fil.write(content)
    yield str(tmpdir / f'tmp{len(os.listdir(tmpdir))-1}.yaml')


@pytest.fixture
def yaml_default_set_twice(tmpdir):
    content = "param: 2"
    with open(tmpdir / f'tmp{len(os.listdir(tmpdir))}.yaml', "w",
              encoding='utf-8') as fil:
        fil.write(content)
    yield str(tmpdir / f'tmp{len(os.listdir(tmpdir))-1}.yaml')


@pytest.fixture
def yaml_experiment_sub_star(tmpdir):
    content = "subconfig2:\n  '*param*': 1.0"
    with open(tmpdir / f'tmp{len(os.listdir(tmpdir))}.yaml', "w",
              encoding='utf-8') as fil:
        fil.write(content)
    yield str(tmpdir / f'tmp{len(os.listdir(tmpdir))-1}.yaml')


@pytest.fixture
def yaml_experiment_sub_dot(tmpdir):
    content = "subconfig2:\n  subconfig3.param4: 1.0"
    with open(tmpdir / f'tmp{len(os.listdir(tmpdir))}.yaml', "w",
              encoding='utf-8') as fil:
        fil.write(content)
    yield str(tmpdir / f'tmp{len(os.listdir(tmpdir))-1}.yaml')


@pytest.fixture
def yaml_craziest_config(tmpdir):
    with open(tmpdir / 'd_first.yaml', "w", encoding='utf-8') as fil:
        fil.write("p1: 1\n"
                  "--- !c1\n"
                  "c2:\n"
                  f"  f_path: {'d_second.yaml'}\n"
                  "---\n"
                  "c4.p3: 3\n"
                  "c4.p7: 7\n"
                  f"f_path: {tmpdir / 'd_second.yaml'}")
    with open(tmpdir / 'd_second.yaml', "w", encoding='utf-8') as fil:
        fil.write("--- !c3\n"
                  "p2: 2\n"
                  f"c5.s_path: {tmpdir / 'd_third.yaml'}\n"
                  "---\n"
                  "p6: 6")
    with open(tmpdir / 'd_third.yaml', "w", encoding='utf-8') as fil:
        fil.write("--- !c6\n"
                  "p4: !type:(dict,int) {a: 4}\n"
                  "---\n"
                  "p5: 5")
    with open(tmpdir / 'e_first.yaml', 'w', encoding='utf-8') as fil:
        fil.write("'*p6': 7\n"
                  "--- !c1\n"
                  f"c2.f_path: {tmpdir / 'e_second.yaml'}\n"
                  "---\n"
                  "c4:\n"
                  "  p3: 'test'\n"
                  "c4.p7: 'test2'")
    with open(tmpdir / 'e_second.yaml', "w", encoding='utf-8') as fil:
        fil.write("--- !c3\n"
                  "'*.p*': 8\n"
                  "'*p4': !type:dict {b: 5}")
    yield str(tmpdir / 'd_first.yaml'), str(tmpdir / 'e_first.yaml')


@pytest.fixture
def yaml_no_file_call_processing_while_loading(tmpdir):
    with open(tmpdir / 'd_first.yaml', "w", encoding='utf-8') as fil:
        fil.write(f"test_path: {tmpdir / 'd_second.yaml'}\nexp_path: null")
    with open(tmpdir / 'd_second.yaml', "w", encoding='utf-8') as fil:
        fil.write("param: 0.1")
    with open(tmpdir / 'e_first.yaml', "w", encoding='utf-8') as fil:
        fil.write(f"exp_path: {tmpdir / 'e_second.yaml'}")
    with open(tmpdir / 'e_second.yaml', "w", encoding='utf-8') as fil:
        fil.write("param: 0.2")
    config = make_config(str(tmpdir / 'd_first.yaml'),
                         str(tmpdir / 'e_first.yaml'),
                         additional_configs_suffix="_path",
                         variations_suffix="var*", grids_suffix="grid",
                         do_not_merge_command_line=True)
    config.save(str(tmpdir / 'save.yaml'))
    with open(tmpdir / 'd_second.yaml', "w", encoding='utf-8') as fil:
        fil.write("param: 0.3")
    with open(tmpdir / 'e_second.yaml', "w", encoding='utf-8') as fil:
        fil.write("param: 0.4")
    config2 = make_config(str(tmpdir / 'd_first.yaml'),
                          str(tmpdir / 'save.yaml'),
                          additional_configs_suffix="_path",
                          variations_suffix="var*", grids_suffix="grid",
                          do_not_merge_command_line=True)
    yield config, config2


@pytest.fixture
def yaml_no_file_call_processing_while_loading_nested(tmpdir):
    with open(tmpdir / 'nd_first.yaml', "w", encoding='utf-8') as fil:
        fil.write(f"c:\n  test_path: {tmpdir / 'nd_second.yaml'}\n  "
                  "exp_path: null")
    with open(tmpdir / 'nd_second.yaml', "w", encoding='utf-8') as fil:
        fil.write("param: 0.1")
    with open(tmpdir / 'ne_first.yaml', "w", encoding='utf-8') as fil:
        fil.write(f"c:\n  exp_path: {tmpdir / 'ne_second.yaml'}")
    with open(tmpdir / 'ne_second.yaml', "w", encoding='utf-8') as fil:
        fil.write("param: 0.2")
    config = make_config(str(tmpdir / 'nd_first.yaml'),
                         str(tmpdir / 'ne_first.yaml'),
                         additional_configs_suffix="_path",
                         variations_suffix="var*", grids_suffix="grid",
                         do_not_merge_command_line=True)
    config.save(str(tmpdir / 'nsave.yaml'))
    with open(tmpdir / 'nd_second.yaml', "w", encoding='utf-8') as fil:
        fil.write("param: 0.3")
    with open(tmpdir / 'ne_second.yaml', "w", encoding='utf-8') as fil:
        fil.write("param: 0.4")
    config2 = make_config(str(tmpdir / 'nd_first.yaml'),
                          str(tmpdir / 'nsave.yaml'),
                          additional_configs_suffix="_path",
                          variations_suffix="var*", grids_suffix="grid",
                          do_not_merge_command_line=True)
    yield config, config2


@pytest.fixture
def yaml_type_check(tmpdir):
    index = len(os.listdir(tmpdir))
    content = (f"root_path: '{tmpdir / f'default_second{index}.yaml'}'\nsubconfig:\n  "
               f"sub_path: '{tmpdir / f'default_second{index}.yaml'}'")
    with open(tmpdir / f'default{index}.yaml', "w", encoding='utf-8') as fil:
        fil.write(content)
    content = ("param_int: !type:int 1\nparam_float: !type:float 0.1\nparam_str: !type:str abc\n"
               "param_bool: !type:bool false\n"
               "param_none: !type:none null\nparam_list: !type:list [0]\nparam_dict: !type:dict\n  a: 0\n"
               "param_any: !type:Any null\nparam_tuple1: !type:(str,float) 0.4\nparam_tuple2: !type:(str,float) ab\n"
               "param_optional1: !type:Optional[int] null\nparam_optional2: !type:Optional[int] 3\n"
               "param_listint: !type:List[int] [0]\nparam_listintstr: !type:List[int,str] [0, ab]\n"
               "param_dictlistoptionalint: !type:Dict[List[Optional[int]]]\n  a: [0, 1, null, 3]")
    with open(tmpdir / f'default_second{index}.yaml', "w",
              encoding='utf-8') as fil:
        fil.write(content)
    yield str(tmpdir / f'default{index}.yaml')


@pytest.fixture
def yaml_tag_assignment_check(tmpdir):
    index = len(os.listdir(tmpdir))
    content = (f"param1: !add_1 0.1\n--- !subconfig1\nparam2: 3.0\n---\n"
               f"def_second_path: '{tmpdir / f'default_second{index}.yaml'}'\n"
               "exp_second_path: null")
    with open(tmpdir / f'default{index}.yaml', "w", encoding='utf-8') as fil:
        fil.write(content)
    content = ("--- !subconfig2\nparam3: 20.0\nsubconfig3:\n  "
               "param4: !copy_param 'param1'")
    with open(tmpdir / f'default_second{index}.yaml', "w",
              encoding='utf-8') as fil:
        fil.write(content)
    yield str(tmpdir / f'default{index}.yaml')


@pytest.fixture
def config_vs_dict_checks(tmpdir):
    index = len(os.listdir(tmpdir))
    content = ("config1:\n"
               "  config2:\n"
               "    param1: !type:dict\n"
               "      key1: !type:dict\n"
               "        key2: 0\n"
               "      key3: ['!type:dict']\n"
               "--- !config3.config4\n"
               "config5:\n"
               "  config6:\n"
               "    param1: !type:dict\n"
               "      key1: !type:dict\n"
               "        key1: 0\n"
               "      key2: ['!type:dict']\n"
               "--- !config10.config11\n"
               "config1.config7:\n"
               "  config8:\n"
               "    param1: !type:dict\n"
               "      key1: !type:dict\n"
               "        key1: 0\n"
               "      key2: ['!type:dict']\n"
               "  config9.param2: null")
    with open(tmpdir / f'default{index}.yaml', "w", encoding='utf-8') as fil:
        fil.write(content)
    yield str(tmpdir / f'default{index}.yaml')


@pytest.fixture
def yaml_last_mapping_reset_on_new_document(tmpdir):
    index = len(os.listdir(tmpdir))
    content = ("--- !c_1\n"
               "p_1_1: []\n"
               "p_1_2: 0\n"
               "--- !c_2\n"
               "p_2_1: []\n"
               "p_2_2: 0\n")
    with open(tmpdir / f'default{index}.yaml', "w", encoding='utf-8') as fil:
        fil.write(content)
    yield str(tmpdir / f'default{index}.yaml')


@pytest.fixture
def yaml_empty_string_in_list(tmpdir):
    index = len(os.listdir(tmpdir))
    content = ('a: [""]')
    with open(tmpdir / f'default{index}.yaml', "w", encoding='utf-8') as fil:
        fil.write(content)
    yield str(tmpdir / f'default{index}.yaml')
