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
import logging
import os.path as osp
from pathlib import Path
from typing import Any

import pytest

from unittests.config.utils import load_config, template
from yaecs import Configuration, Experiment, Priority, assign_order, assign_yaml_tag
from yaecs.user_utils import make_config
from yaecs.yaecs_utils import compare_string_pattern


def check_integrity(config, p_1: Any = 0.1, p_2: Any = 2.0, p_3: Any = 30.0,
                    p_4: Any = "string"):
    assert config["param1"] == p_1
    assert config["subconfig1.param2"] == p_2
    assert config["subconfig2.param3"] == p_3
    assert config["subconfig2.subconfig3.param4"] == p_4


def test_load_default(capsys, yaml_default):
    config = load_config(default_config=yaml_default)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    assert 1 != config
    assert config != 1
    check_integrity(config, p_2=3.0, p_3=20.0)
    config = template(default_config=yaml_default).load_config(
        [], do_not_merge_command_line=True)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    assert 1 != config
    assert config != 1
    check_integrity(config, p_2=3.0, p_3=20.0)
    config2 = config.copy()
    config2.merge({"subconfig2.subconfig3.param4": "new_string"})
    assert config != config2
    assert config2 != config
    config2 = config.copy()
    object.__setattr__(config2.subconfig2, "subconfig3", 1)
    assert config != config2
    assert config2 != config
    config2 = config.copy()
    object.__delattr__(config2.subconfig2, "subconfig3")
    assert config != config2
    assert config2 != config
    assert config == template(default_config=yaml_default).build_from_configs(
        template(default_config=yaml_default).get_default_config_path(),
        do_not_merge_command_line=True)


def test_load_experiment(capsys, yaml_default, yaml_experiment,
                         yaml_experiment_sub_dot, yaml_experiment_sub_star):
    config = load_config(yaml_experiment, default_config=yaml_default)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    check_integrity(config)
    assert config == template(default_config=yaml_default).build_from_configs([
        template(default_config=yaml_default).get_default_config_path(),
        yaml_experiment
    ], do_not_merge_command_line=True)
    config = load_config(yaml_experiment_sub_dot, default_config=yaml_default)
    check_integrity(config, p_2=3.0, p_3=20.0, p_4=1.0)
    config = load_config(yaml_experiment_sub_star, default_config=yaml_default)
    check_integrity(config, p_2=3.0, p_3=1.0, p_4=1.0)


def test_get(caplog):
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        config = make_config({
            "save": "test",
            "param": 1
        }, do_not_merge_command_line=True)
    assert caplog.text.count("WARNING") == 2
    assert config["param"] == 1
    assert config["save"] == "test"
    assert config["___save"] == "test"
    assert config.param == 1
    assert config.___save == "test"  # pylint: disable=protected-access
    assert callable(config.save)
    assert config.get("param", None) == 1
    assert config.get("save", None) == "test"
    assert config.get("___save", None) == "test"
    assert config.get("not_a_param", None) is None
    assert config.get("param.param", None) is None


def test_get_dict(yaml_default):
    config = load_config(default_config=yaml_default)
    object.__setattr__(config, "___save", "test")
    def_second = osp.join(
        osp.sep.join(yaml_default.split(osp.sep)[:-1]),
        ('default_second'
         f'{yaml_default.split(osp.sep)[-1][len("default"):-len(".yaml")]}'
         '.yaml'))
    assert config.get_dict() == {
        'param1': 0.1,
        'subconfig1': {
            'param2': 3.0
        },
        'subconfig2': {
            'param3': 20.0,
            'subconfig3': {
                'param4': 'string'
            }
        },
        'def_second_path': def_second,
        'exp_second_path': None,
        'save': 'test'
    }
    assert config['param1'] == 0.1
    assert config['def_second_path'] == def_second
    assert config['exp_second_path'] is None
    assert config['save'] == 'test'
    assert isinstance(config['subconfig1'], Configuration)
    assert isinstance(config['subconfig2'], Configuration)
    config = make_config({"a": 1}, post_processing_dict={"a": lambda x: x + 1})
    assert config.get_dict(pre_post_processing_values=True) == {"a": 1}
    assert config.get_dict(pre_post_processing_values=False) == {"a": 2}


def test_iter(yaml_default):
    config = load_config(default_config=yaml_default)
    object.__setattr__(config, "___save", "test")
    dict_for_test = {
        'param1': 0,
        'subconfig1': 0,
        'subconfig2': 0,
        'def_second_path': 0,
        'exp_second_path': 0,
        'save': 0
    }
    for k in config:
        dict_for_test[k] += 1
        assert dict_for_test[k] == 1
    assert len(dict_for_test) == 6


def test_keys_values_items(yaml_default):
    config = load_config(default_config=yaml_default)
    object.__setattr__(config, "___save", "test")
    def_second = osp.join(
        osp.sep.join(yaml_default.split(osp.sep)[:-1]),
        ('default_second'
         f'{yaml_default.split(osp.sep)[-1][len("default"):-len(".yaml")]}'
         '.yaml'))
    # deep = False (default)
    expected_dict = {
        'param1': 0.1,
        'subconfig1': config.subconfig1,
        'subconfig2': config.subconfig2,
        'def_second_path': def_second,
        'exp_second_path': None,
        'save': 'test'
    }
    assert config.items() == expected_dict.items()
    assert config.keys() == expected_dict.keys()
    assert list(config.values()) == list(expected_dict.values())
    # deep = True
    expected_dict_deep = {
        'param1': 0.1,
        'subconfig1': {
            'param2': 3.0
        },
        'subconfig2': {
            'param3': 20.0,
            'subconfig3': {
                'param4': 'string'
            }
        },
        'def_second_path': def_second,
        'exp_second_path': None,
        'save': 'test'
    }
    assert config.items(deep=True) == expected_dict_deep.items()
    assert list(config.values(deep=True)) == list(expected_dict_deep.values())


def test_merge_pattern(capsys, yaml_default, yaml_experiment):
    config = load_config(yaml_experiment, default_config=yaml_default)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    config.merge({"param*": 0.2})
    check_integrity(config, 0.2)
    config.merge({"*param*": 0.2})
    check_integrity(config, 0.2, 0.2, 0.2, 0.2)
    config.subconfig2.merge({"*param*": 0.4})
    check_integrity(config, 0.2, 0.2, 0.4, 0.4)
    assert config.config_metadata["config_hierarchy"] == [
        yaml_default, yaml_experiment, {
            'param*': 0.2
        }, {
            '*param*': 0.2
        }, {
            'subconfig2.*param*': 0.4
        }
    ]
    config.subconfig2.subconfig3.merge({"*param*": "0.5"})
    check_integrity(config, 0.2, 0.2, 0.4, "0.5")
    assert config.config_metadata["config_hierarchy"] == [
        yaml_default, yaml_experiment, {
            'param*': 0.2
        }, {
            '*param*': 0.2
        }, {
            'subconfig2.*param*': 0.4
        }, {
            'subconfig2.subconfig3.*param*': "0.5"
        }
    ]


def test_merge_from_command_line(caplog, yaml_default, yaml_experiment):

    def mcl(cfg, string):
        # pylint: disable=protected-access
        to_merge = cfg._gather_command_line_dict(to_merge=string)
        if to_merge:
            logging.getLogger("yaecs.config").info(f"Merging from command line : {to_merge}")
            cfg._merge(to_merge)

    caplog.clear()
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        config = load_config(yaml_experiment, default_config=yaml_default)
    assert caplog.text.count("WARNING") == 0
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        mcl(config, "--lr=0.5 --param1=1 --subconfig1.param2=0.6")
    assert caplog.text.count("WARNING") == 2
    assert (("WARNING : parameters ['lr'], encountered while merging params from "
             "the command line, do not match any param in the config")
            in caplog.text)
    caplog.clear()
    check_integrity(config, 1, 0.6)

    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        mcl(config, "--subconfig2.subconfig3.param4='test test'")
    assert caplog.text.count("WARNING") == 0
    caplog.clear()
    check_integrity(config, 1, 0.6, p_4="test test")
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        config_2 = load_config(yaml_experiment, default_config=yaml_default)
        mcl(config_2, config.get_command_line_argument(do_return_string=True))
    assert caplog.text.count("WARNING") == 0
    caplog.clear()
    check_integrity(config_2, 1, 0.6, p_4="test test")
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        mcl(config_2, "--param1 2 --*param2=null --*param3=\\\"null\\\" "
                      "--*param4= [ 1  ,0.5 , {string: \\\"\\'[as \\!a \\\"}] ")
    assert caplog.text.count("WARNING") == 0
    caplog.clear()
    check_integrity(config_2, 2, None, "null", p_4=[1, 0.5, {"string": "'[as !a "}])
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        mcl(config, config_2.get_command_line_argument(do_return_string=True))
    assert caplog.text.count("WARNING") == 0
    caplog.clear()
    check_integrity(config_2, 2, None, "null", p_4=[1, 0.5, {"string": "'[as !a "}])
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        mcl(config, "--subconfig1.param2")
    assert caplog.text.count("WARNING") == 0
    assert config.subconfig1.param2 is True
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        mcl(config, "--subconfig1.param2=False")
    assert caplog.text.count("WARNING") == 0
    assert config.subconfig1.param2 is False
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        mcl(config, "--subconfig1.param2=yes")
    assert caplog.text.count("WARNING") == 0
    assert config.subconfig1.param2 is True


def test_method_name(caplog):
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        config = make_config({"save": "test"}, do_not_merge_command_line=True)
    assert caplog.text.count("WARNING") == 2
    assert config.details() == ("\nMAIN CONFIG :\nConfiguration hierarchy :\n>"
                                " {'save': 'test'}\n\n - save : test\n")
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        config.merge({"save": 0.1})
    assert caplog.text.count("WARNING") == 0
    assert config.details() == ("\nMAIN CONFIG :\nConfiguration hierarchy :\n>"
                                " {'save': 'test'}\n> {'save': 0.1}\n\n"
                                " - save : 0.1\n")


def test_details(yaml_default, yaml_experiment):
    config = load_config(yaml_experiment, default_config=yaml_default)
    ref_str = (f"\nMAIN CONFIG :\nConfiguration hierarchy :\n> {yaml_default}"
               f"\n> {yaml_experiment}\n\n - param1 : 0.1\n - subconfig1 : "
               "\n\tSUBCONFIG1 CONFIG :\n\t - param2 : 2.0\n\n - subconfig2 : "
               "\n\tSUBCONFIG2 CONFIG :\n\t - param3 : 30.0\n\t - subconfig3 :"
               " \n\t\tSUBCONFIG3 CONFIG :\n\t\t - param4 : string\n\n\n")
    assert config.details(no_show="*_path") == ref_str
    ref_str = (f"\nMAIN CONFIG :\nConfiguration hierarchy :\n> {yaml_default}"
               f"\n> {yaml_experiment}\n\n - param1 : 0.1\n - subconfig1 : "
               "SUBCONFIG1\n - subconfig2 : \n	SUBCONFIG2 CONFIG :\n\t "
               "- param3 : 30.0\n\t - subconfig3 : \n\t\tSUBCONFIG3 CONFIG :\n"
               "\t\t - param4 : string\n\n\n")
    assert config.details(expand_only=["subconfig2"],
                          no_show="*_path") == ref_str
    ref_str = (f"\nMAIN CONFIG :\nConfiguration hierarchy :\n> {yaml_default}"
               f"\n> {yaml_experiment}\n\n - param1 : 0.1\n - subconfig1 : \n"
               "\tSUBCONFIG1 CONFIG :\n\t - param2 : 2.0\n\n - subconfig2 : "
               "SUBCONFIG2\n")
    assert config.details(no_expand=["subconfig2"],
                          no_show="*_path") == ref_str


def test_variations(capsys, yaml_default):
    config = make_config(
        {
            "p1": 0.1,
            "p2": 1.0,
            "var1": [{
                "p1": 0.1
            }, {
                "p1": 0.2
            }],
            "var2": [{
                "p2": 1.0
            }, {
                "p2": 2.0
            }, {
                "p2": 3.0
            }],
            "grid": None,
            "tracker_config": {"type": []}
        }, config_class=template(yaml_default), do_not_merge_command_line=True)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    assert config.p1 == 0.1 and config.p2 == 1.0
    variations = config.create_variations()
    assert len(variations) == 5
    assert variations[0] == variations[2] == config
    assert variations[1].p1 == 0.2 and variations[1].p2 == 1.0
    assert variations[3].p1 == variations[4].p1 == 0.1
    assert variations[3].p2 == 2.0 and variations[4].p2 == 3.0
    config.merge({"grid": ["var1", "var2"]})
    variations = config.create_variations()
    assert len(variations) == 6
    assert (variations[0] == config
            and variations[1].p1 == variations[2].p1 == 0.1
            and variations[3].p2 == 1.0)
    assert variations[3].p1 == variations[4].p1 == variations[5].p1 == 0.2
    assert (variations[1].p2 == variations[4].p2 == 2.0
            and variations[2].p2 == variations[5].p2 == 3.0)

    def _main(config, tracker):
        return
    Experiment(config, _main, experiment_name="test", run_name="test").run(run_description="")


def test_pre_processing(capsys, tmp_file_name,
                        yaml_no_file_call_processing_while_loading,
                        yaml_default,
                        yaml_no_file_call_processing_while_loading_nested,
                        yaml_default_preproc_default_dot_param,
                        yaml_experiment):
    preprocessing = {
        "*param*": lambda x: x + 1 if not isinstance(x, str) else x
    }
    config = load_config(default_config=yaml_default_preproc_default_dot_param,
                         preprocessing=preprocessing)
    assert config.param1.param2 == 3
    config = load_config(yaml_experiment, default_config=yaml_default,
                         preprocessing=preprocessing)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    check_integrity(config, 1.1, 3.0, 31.0)
    config.save(str(tmp_file_name))
    config2 = load_config(str(tmp_file_name), default_config=yaml_default,
                          preprocessing=preprocessing)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    assert config == config2
    config2.merge({"param1": 0.2})
    assert config2.param1 == 1.2
    assert (yaml_no_file_call_processing_while_loading[0] ==
            yaml_no_file_call_processing_while_loading[1])
    assert (yaml_no_file_call_processing_while_loading_nested[0] ==
            yaml_no_file_call_processing_while_loading_nested[1])


def test_post_processing(capsys, yaml_default, yaml_experiment, tmp_file_name,
                         yaml_default_preproc_default_dot_param):
    # Does post-processing work after load_config ?
    postprocessing = {
        "*param*": lambda x: x + 1 if not isinstance(x, str) else x
    }
    config = load_config(default_config=yaml_default_preproc_default_dot_param,
                         postprocessing=postprocessing)
    assert config.param1.param2 == 3
    config = load_config(yaml_experiment, default_config=yaml_default,
                         postprocessing=postprocessing)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    check_integrity(config, 1.1, 3.0, 31.0)
    config.save(str(tmp_file_name))
    config2 = load_config(str(tmp_file_name), default_config=yaml_default,
                          postprocessing=postprocessing)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    assert config == config2
    config2 = load_config(str(tmp_file_name), default_config=yaml_default)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    check_integrity(config2)
    # Does post-processing work after manual merge ?
    config = load_config(default_config=yaml_default_preproc_default_dot_param,
                         postprocessing=postprocessing)
    config.merge(yaml_default_preproc_default_dot_param)
    assert config.param1.param2 == 3
    config = load_config({}, default_config=yaml_default,
                         postprocessing=postprocessing)
    config.merge(yaml_experiment)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    check_integrity(config, 1.1, 3.0, 31.0)
    config.save(str(tmp_file_name))
    config2 = load_config({}, default_config=yaml_default,
                          postprocessing=postprocessing)
    config2.merge(str(tmp_file_name))
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    assert config == config2
    config2 = load_config({}, default_config=yaml_default)
    config2.merge(str(tmp_file_name))
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    check_integrity(config2)

    # Does post-processing interact correctly with save ?

    class Storage:
        """Test class for config storage."""

        def __init__(self, **kwargs):
            self.stored = kwargs

        def __eq__(self, other):
            return self.stored == other.stored

        def __repr__(self):
            return f"<Storage: {self.stored}>"

    postprocessing = {"*to_store": lambda x: Storage(**x)}
    default = {
        "a": 10,
        "b.to_store": {
            "i": 1,
            "j": 2
        }
    }
    config = make_config(default, post_processing_dict=postprocessing)
    config.save(str(tmp_file_name))
    assert config == make_config(default, str(tmp_file_name),
                                 post_processing_dict=postprocessing)
    assert make_config(default, str(tmp_file_name)).b.to_store == {"i": 1, "j": 2}
    assert make_config(default, str(tmp_file_name)).a == 10
    # Does post-processing interact correctly with get_command_line_arguments ?
    config = make_config({
        "a": 10,
        "b.to_store": {
            "i": 1,
            "j": 2
        }
    }, post_processing_dict=postprocessing)
    dico = config._gather_command_line_dict(  # pylint: disable=protected-access
        config.get_command_line_argument(do_return_string=True))
    assert config == make_config(dico, post_processing_dict=postprocessing)
    assert make_config(dico).b.to_store == {"i": 1, "j": 2}
    assert make_config(dico).a == 10


def test_post_processing_modify(yaml_default, yaml_experiment):

    class TestConfig(Configuration):
        @staticmethod
        def get_default_config_path():
            return yaml_default

        def post_processing_func1(self, param1):
            object.__setattr__(self.get_main_config().subconfig1, "param2", 4)
            return param1 + 1

        def post_processing_func2(self, param4):
            object.__setattr__(self.get_main_config().subconfig2, "param3", 5)
            return param4 + "_"

        def parameters_pre_processing(self):
            return {
                "*_path": self.register_as_additional_config_file
            }

        def parameters_post_processing(self):
            return {
                "param1": self.post_processing_func1,
                "subconfig2.subconfig3.param4": self.post_processing_func2
            }
    config = TestConfig.load_config(yaml_experiment, do_not_merge_command_line=True)
    check_integrity(config, p_1=1.1, p_2=4, p_3=5, p_4="string_")


def test_save_reload(capsys, tmp_file_name, yaml_default, yaml_experiment):
    config = load_config(yaml_experiment, default_config=yaml_default)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    config.save(str(tmp_file_name))
    config2 = load_config(str(tmp_file_name), default_config=yaml_default)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    config2.save(str(tmp_file_name))
    config3 = load_config(str(tmp_file_name), default_config=yaml_default)
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out
    assert config == config2 == config3


def test_save_reload_method_param(caplog, tmp_file_name):
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        config = make_config({"save": 1}, do_not_merge_command_line=True)
    assert caplog.text.count("WARNING") == 2
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        config.save(str(tmp_file_name))
        config2 = make_config({"save": 1}, do_not_merge_command_line=True)
        config2.merge(str(tmp_file_name))
    assert caplog.text.count("WARNING") == 2
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        config2.save(str(tmp_file_name))
        config3 = make_config({"save": 1}, do_not_merge_command_line=True)
        config3.merge(str(tmp_file_name))
    assert caplog.text.count("WARNING") == 2
    config3.save(str(tmp_file_name))
    assert config == config2 == config3


def test_craziest_config(yaml_craziest_config, tmp_file_name):

    class Storage:
        """Test class for config storage."""

        def __init__(self, **kwargs):
            self.stored = kwargs

        def __repr__(self):
            return f"<STORED: {self.stored}>"

        def __eq__(self, other):
            return self.stored == other.stored

    post_processing = {"*p4": lambda x: Storage(**x)}
    config = make_config(yaml_craziest_config[0],
                         do_not_merge_command_line=True,
                         additional_configs_suffix="_path")
    second = osp.join(
        Path(yaml_craziest_config[0]).parents[0], "d_second.yaml")
    third = osp.join(Path(yaml_craziest_config[0]).parents[0], "d_third.yaml")
    dico_str = "{'a': 4}"
    dico_str2 = "{'b': 5}"
    ref_str = (f"\nMAIN CONFIG :\nConfiguration hierarchy :\n"
               f"> {yaml_craziest_config[0]}\n\n - p1 : 1\n - c1 : \n\t"
               "C1 CONFIG :\n\t - c2 : \n\t	C2 CONFIG :\n\t\t - c3 : "
               "\n\t\t\tC3 CONFIG :\n\t\t\t - p2 : 2\n\t\t\t - c5 : "
               "\n\t\t\t\tC5 CONFIG :\n\t\t\t\t - c6 : \n\t\t\t\t\tC6 CONFIG :"
               f"\n\t\t\t\t\t - p4 : {dico_str}\n\n\t\t\t\t - p5 : 5\n\t\t\t\t"
               f" - s_path : {third}\n\n\n\t\t - p6 : 6\n\t\t - f_path : "
               "d_second.yaml\n\n\n - c4 : \n\tC4 CONFIG :\n\t - p3 : 3\n\t "
               "- p7 : 7\n\n - c3 : \n\tC3 CONFIG :\n\t - p2 : 2\n\t - c5 : "
               "\n\t\tC5 CONFIG :\n\t\t - c6 : \n\t\t\tC6 CONFIG :\n\t\t\t "
               f"- p4 : {dico_str}\n\n\t\t - p5 : 5\n\t\t - s_path : {third}"
               f"\n\n\n - p6 : 6\n - f_path : {second}\n")
    assert config.details() == ref_str
    config = make_config(yaml_craziest_config[0], yaml_craziest_config[1],
                         do_not_merge_command_line=True,
                         additional_configs_suffix="_path",
                         post_processing_dict=post_processing)
    second_e = osp.join(
        Path(yaml_craziest_config[0]).parents[0], "e_second.yaml")
    ref_str = (f"\nMAIN CONFIG :\nConfiguration hierarchy :\n> "
               f"{yaml_craziest_config[0]}\n> {yaml_craziest_config[1]}\n\n"
               " - p1 : 1\n - c1 : \n	C1 CONFIG :\n\t - c2 : \n\t	C2 CONFIG"
               " :\n\t\t - c3 : \n\t\t\tC3 CONFIG :\n\t\t\t - p2 : 2\n\t\t\t "
               "- c5 : \n\t\t\t\tC5 CONFIG :\n\t\t\t\t - c6 : \n\t\t\t\t\tC6 "
               f"CONFIG :\n\t\t\t\t\t - p4 : <STORED: {dico_str2}>\n\n\t\t\t\t"
               f" - p5 : 8\n\t\t\t\t - s_path : {third}\n\n\n\t\t - p6 : 7"
               f"\n\t\t - f_path : {second_e}\n\n\n - c4 : \n\tC4 CONFIG :"
               "\n\t - p3 : test\n\t - p7 : test2\n\n - c3 : \n\tC3 CONFIG :"
               "\n\t - p2 : 2\n\t - c5 : \n\t\tC5 CONFIG :\n\t\t - c6 : "
               f"\n\t\t\tC6 CONFIG :\n\t\t\t - p4 : <STORED: {dico_str}>"
               f"\n\n\t\t - p5 : 5\n\t\t - s_path : {third}\n\n\n - p6 : 7"
               f"\n - f_path : {second}\n")
    assert ref_str == config.details()
    config.save(str(tmp_file_name))
    config2 = make_config(yaml_craziest_config[0], str(tmp_file_name),
                          do_not_merge_command_line=True,
                          additional_configs_suffix="_path",
                          post_processing_dict=post_processing)
    assert config == config2
    dico = config._gather_command_line_dict(  # pylint: disable=protected-access
        config.get_command_line_argument(do_return_string=True))
    assert config == make_config(dico, post_processing_dict=post_processing)


def test_pattern_matching():
    assert compare_string_pattern("", "*")
    assert compare_string_pattern("abcdefgh0123,:", "*")
    assert compare_string_pattern("abcdefgh0123", "abcdefgh0123")
    assert compare_string_pattern("abcdefgh0123", "abcde*gh0123")
    assert compare_string_pattern("abcdeffffgh0123", "abcde*gh0123")
    assert compare_string_pattern("abcdefgh0123", "*a*b*c*d*e*f*g*h*0*1*2*3*")
    assert compare_string_pattern("abcdefgh0123", "*0123")
    assert compare_string_pattern("abcdefgh0123", "abcd*")
    assert compare_string_pattern("abcdefgh0123", "a**3")

    assert not compare_string_pattern("abcdefgh0123", "abcdefgh012")
    assert not compare_string_pattern("abcdefgh0123", "abcde*g0123")
    assert not compare_string_pattern("abcdefgh0123ffffh0123", "abcde*gh0123")
    assert not compare_string_pattern("abcdefgh0123", "*3*3*3")


def test_typecheck(yaml_type_check):
    load_config(default_config=yaml_type_check)


def test_yaml_tag_assignment(yaml_tag_assignment_check):
    template_class = template(default_config=yaml_tag_assignment_check)

    @assign_yaml_tag("add_1", "post", "float")
    def add_1(self, param):
        return param + 1

    template_class.add_1 = add_1
    config = template_class.load_config(do_not_merge_command_line=True)
    check_integrity(config, p_1=1.1, p_2=3.0, p_3=20.0, p_4=1.1)


def test_yaml_order(yaml_default):
    @assign_order(Priority.SITUATIONAL)
    def add_1(value):
        return value + 1

    @assign_order(Priority.OFTEN_FIRST)
    def double_value_first(value):
        return value * 2

    @assign_order(Priority.OFTEN_LAST)
    def double_value_last(value):
        return value * 2
    postprocessing = {"param1": add_1, "param1 ": double_value_first}
    config = load_config(default_config=yaml_default, postprocessing=postprocessing)
    check_integrity(config, p_1=1.2, p_2=3.0, p_3=20.0)
    postprocessing = {"param1": add_1, "param1 ": double_value_last}
    config = load_config(default_config=yaml_default, postprocessing=postprocessing)
    check_integrity(config, p_1=2.2, p_2=3.0, p_3=20.0)


def test_compose(yaml_default):
    def add_1(value):
        return value + 1

    def double_value(value):
        return value * 2

    postprocessing = {"param1": (add_1, double_value)}
    config = load_config(default_config=yaml_default, postprocessing=postprocessing)
    check_integrity(config, p_1=2.2, p_2=3.0, p_3=20.0)


def test_config_vs_dict_checks(caplog, config_vs_dict_checks):

    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        config = load_config(default_config=config_vs_dict_checks)
    assert caplog.text.count("WARNING") == 0
    string = f"\nMAIN CONFIG :\nConfiguration hierarchy :\n> {config_vs_dict_checks}" \
             "\n\n - config1 : \n	CONFIG1 CONFIG :\n	 - config2 : \n		CONFIG2 CONFIG :\n" \
             "		 - param1 : {'key1': {'key2': 0}, 'key3': ['!type:dict']}\n\n\n - config3 : \n	CONFIG3 CONFIG :" \
             "\n	 - config4 : \n		CONFIG4 CONFIG :\n		 - config5 : \n			CONFIG5 CONFIG :" \
             "\n			 - config6 : \n				CONFIG6 CONFIG :\n				 - param1 : {'key1': {'key1':" \
             " 0}, 'key2': ['!type:dict']}\n\n\n\n\n - config10 : \n	CONFIG10 CONFIG :\n	 - config11 : " \
             "\n		CONFIG11 CONFIG :\n		 - config1 : \n			CONFIG1 CONFIG :\n			 - config7 : " \
             "\n				CONFIG7 CONFIG :\n				 - config8 : \n					CONFIG8 CONFIG :" \
             "\n					 - param1 : {'key1': {'key1': 0}, 'key2': ['!type:dict']}\n\n				 - co" \
             "nfig9 : \n					CONFIG9 CONFIG :\n					 - param2 : None\n\n\n\n\n\n"
    assert config.details() == string


def test_warnings(caplog, tmp_file_name):

    caplog.clear()
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        config = make_config({"param": 1}, do_not_merge_command_line=True,
                             overwriting_regime="unsafe")
        config.save(str(tmp_file_name))
        config.merge(str(tmp_file_name))
    assert caplog.text.count("YOU ARE LOADING AN UNSAFE CONFIG") == 1
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        config = make_config({"param": 1}, do_not_merge_command_line=True)
        config.merge({"*d": 1})
    assert caplog.text.count("will be ignored : it does not match any") == 1


def test_errors(caplog, yaml_default_sub_variations,
                yaml_default_set_twice, yaml_default, yaml_type_check):
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        logging.getLogger("yaecs").propagate = True
        with pytest.raises(
                Exception, match="'overwriting_regime' needs to be "
                                 "either 'auto-save', 'locked' or 'unsafe'."):
            _ = make_config({"param": 1}, do_not_merge_command_line=True,
                            overwriting_regime="a")
        with pytest.raises(
                Exception, match=".*is not a sub-config, it "
                                 "cannot be accessed.*"):
            _ = make_config({"param": 1},
                            do_not_merge_command_line=True)["param.param"]
        with pytest.raises(
                Exception, match="Overwriting params in locked "
                                 "configs is not allowed."):
            config = make_config({"param": 1}, do_not_merge_command_line=True,
                                 overwriting_regime="locked")
            config.param = 2
        with pytest.raises(
                Exception, match="build_from_configs needs to be "
                                 "called with at least one config."):
            _ = template().build_from_configs(do_not_merge_command_line=True)
        with pytest.raises(
                Exception, match="build_from_configs needs to be "
                                 "called with at least one config."):
            _ = template().build_from_configs([], do_not_merge_command_line=True)
        with pytest.raises(Exception, match=".*\nplease use build_from_configs.*"):
            _ = template().build_from_configs(
                [template(default_config=yaml_default).get_default_config_path()],
                [{
                    "param1": 1
                }], do_not_merge_command_line=True)
        with pytest.raises(Exception, match="No filename was provided.*"):
            make_config({"param": 1}).save()
        with pytest.raises(Exception, match="Grid element.*"):
            _ = make_config({
                "param": 1,
                "var": [],
                "grid": ["var"]
            }, config_class=template()).create_variations()
        with pytest.raises(Exception, match="Grid element.*"):
            _ = make_config({
                "param": 1,
                "grid": ["var"]
            }, config_class=template()).create_variations()
        with pytest.raises(Exception, match="Variations parsing failed.*"):
            make_config({"param": 1, "var": 1}, config_class=template())
        with pytest.raises(Exception, match="Variations parsing failed.*"):
            make_config({"param": 1, "var": [1]}, config_class=template())
        with pytest.raises(Exception, match="Variations parsing failed.*"):
            make_config({"param": 1, "var": {"a": 1}}, config_class=template())
        with pytest.raises(Exception, match="Grid parsing failed.*"):
            make_config({"param": 1, "grid": {}}, config_class=template())
        with pytest.raises(Exception, match="No YAML file found at path .*"):
            template()(config_path_or_dictionary="not_found")
        with pytest.raises(Exception, match="'config_metadata' is a "
                                            "special parameter.*"):
            make_config({"config_metadata": 1})
        with pytest.raises(
                Exception, match="'overwriting_regime' is a "
                                 "special parameter.*"):
            metadata = ("Saving time : 0 (0) ; Regime : "
                        "something_incorrect")
            make_config({"config_metadata": metadata})
        with pytest.raises(Exception, match="Failed to set parameter.*"):
            config = make_config({"param": 1})
            config.merge({"param.param": 1})
        with pytest.raises(Exception, match="Failed to set parameter.*"):
            _ = make_config({"param": 1, "param.param": 1})
        with pytest.raises(
                Exception, match=".*character is not authorised "
                                 "in the default config.*"):
            _ = make_config({"param*": 1})
    assert caplog.text.count("ERROR while processing param") == 4
    with pytest.raises(
            Exception, match=".*Please declare all your variations "
            "in the main config.*"):
        _ = make_config(yaml_default_sub_variations, config_class=template())
    with pytest.raises(
            Exception, match=".*is a protected name and cannot be "
            "used as a parameter.*"):
        _ = make_config({"_nesting_hierarchy": 1})
    with pytest.raises(
            Exception, match=".*cannot be merged : 'subconfig' is not in the"
            " default.*"):
        config = make_config({"param": 1})
        config.merge({"subconfig.param": 1})
    with pytest.raises(
            Exception, match=".*cannot be merged : 'param2' is not in the"
            " default.*"):
        config = make_config({"param": 1})
        config.merge({"param2": 1})
    with pytest.raises(Exception, match=".*This replacement cannot be "
                       "performed.*"):
        config = make_config({"subconfig.param": 1})
        config.merge({"subconfig": 1})
    with pytest.raises(Exception, match=".* was set twice.*"):
        _ = make_config({
            "param": 1,
            "set_twice_path": yaml_default_set_twice
        }, config_class=template())
    replacements = {
        "param_int": 1.2,
        "param_float": "q",
        "param_str": None,
        "param_none": [],
        "param_bool": {},
        "param_list": True,
        "param_dict": 5,
        "param_listint": [0, 2, "3"],
        "param_listintstr": ["q", 1],
        "param_dictlistoptionalint": {"a": [None], "b": [1, None, 2.5]}
    }
    for k, v in replacements.items():
        for prefix in ["", "subconfig."]:
            with pytest.raises(Exception, match=".*has incorrect type '.*"):
                print(f"Testing for {prefix + k}")
                c = load_config(default_config=yaml_type_check)
                c.merge({prefix + k: v})


def test_empty_string_in_list(yaml_empty_string_in_list):
    config = load_config(default_config=yaml_empty_string_in_list)
    assert config.a == [""]


def test_last_mapping_reset_on_new_document(yaml_last_mapping_reset_on_new_document):
    config = load_config(default_config=yaml_last_mapping_reset_on_new_document)
    assert config.c_1.p_1_1 == []
    assert config.c_1.p_1_2 == 0
    assert config.c_2.p_2_1 == []
    assert config.c_2.p_2_2 == 0
