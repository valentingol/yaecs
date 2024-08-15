""" YAMLScanner class to pre-parse YAML files before feeding it to the config """

import logging
import re
from typing import Any, Dict, Optional, Type

import yaml

from ..yaecs_utils import parse_type, YAML_EXPRESSIONS

YAECS_LOGGER = logging.getLogger(__name__)


class YAMLScanner:
    """ YAMLScanner class to pre-parse YAML files before feeding it to the config """

    def __init__(self, yaml_path: str):
        self.path: str = yaml_path
        self.params: Dict[str, Any] = {}
        self.type_hints: Dict[str, str] = {}
        self.processing_functions: Dict[str, str] = {}
        self.state: Dict[str, Any] = {
            "currently_processed_path": [],
            "last_non_scalar": 0,
            "sequence_depth": [],
        }
        with open(yaml_path, encoding='utf-8') as yaml_file:
            list(yaml.load_all(yaml_file, Loader=self._get_yaml_loader()))

    def resolve_node(self, yaml_loader, tag, node):
        """ Resolve a YAML node to a Python object. """

        with NoTag(yaml_loader):
            if isinstance(node, yaml.ScalarNode):
                if node.value == "":
                    def _can_be_str(parsed_type):
                        if parsed_type is str:
                            return True
                        if isinstance(parsed_type, tuple):
                            if str in parsed_type:
                                return True
                            return any(_can_be_str(t) for t in parsed_type)
                        return False
                    if _can_be_str(parse_type(tag[len("!type:"):])):
                        return yaml_loader.default_yaml_constructors["tag:yaml.org,2002:str"](yaml_loader, node)
                for key, value in YAML_EXPRESSIONS.items():
                    if value.match(node.value):
                        return yaml_loader.default_yaml_constructors[f"tag:yaml.org,2002:{key}"](yaml_loader, node)
                return yaml_loader.construct_scalar(node)
            if isinstance(node, yaml.SequenceNode):
                return yaml_loader.construct_sequence(node, deep=True)
            if isinstance(node, yaml.MappingNode):
                return yaml_loader.construct_mapping(node, deep=True)
            raise ValueError(f"Unsupported node type {type(node)}.")

    def update_state(self, yaml_loader, tag, node):
        """ Updates the state of the scanner as it parses the YAML file. """

        self.state["is_param_tag"] = bool(yaml_loader.constructed_objects) or tag.lower() == "!:no-tag:"
        self.state["resolving_recursive_param"] = yaml_loader.DEFAULT_MAPPING_TAG == "!:no-tag:"
        mapping_added = yaml_loader.constructed_objects and isinstance(
            list(yaml_loader.constructed_objects.keys())[-1], yaml.MappingNode)
        sequence_added = yaml_loader.constructed_objects and isinstance(
            list(yaml_loader.constructed_objects.keys())[-1], yaml.SequenceNode)
        node_type = "scalar" if isinstance(node, yaml.ScalarNode) else "sequence" if isinstance(
            node, yaml.SequenceNode) else "mapping"

        if node_type == "sequence":
            self.state["sequence_depth"].append("sequence")
        if sequence_added:
            self.state["sequence_depth"].pop(-1)
        if self.state["sequence_depth"]:
            if node_type == "mapping":
                self.state["sequence_depth"].append("mapping")
            if mapping_added:
                self.state["sequence_depth"].pop(-1)
        if node_type == "mapping" or mapping_added or sequence_added:
            self.state["last_non_scalar"] = len(yaml_loader.constructed_objects)

        key_counter = len(yaml_loader.constructed_objects) - self.state["last_non_scalar"]
        if self.state["sequence_depth"] and self.state["sequence_depth"][-1] == "sequence":
            self.state["is_key_node"] = False
        else:
            self.state["is_key_node"] = node_type == "scalar" and self.state["is_param_tag"] and key_counter % 2 == 0

    def _get_yaml_loader(self) -> Type[yaml.FullLoader]:
        """ Used to get a custom YAML loader capable of parsing config tags. """

        def generic_constructor(yaml_loader, tag, node):

            self.update_state(yaml_loader, tag, node)

            if self.state["is_key_node"]:
                return yaml_loader.default_yaml_constructors["tag:yaml.org,2002:str"](yaml_loader, node)

            if self.state["is_param_tag"]:
                if self.state["resolving_recursive_param"]:
                    return self.resolve_node(yaml_loader, tag, node)

                name = yaml_loader.constructed_objects[list(yaml_loader.constructed_objects.keys())[-1]]
                check_valid_param_name(name, f"Invalid name '{name}' found in file {self.path} : " + "{issue}.")
                full_name = ".".join(self.state["currently_processed_path"] + [name])

                if tag.lower() != "!type:config":
                    if tag.lower().startswith("!type:"):
                        self.type_hints[full_name] = tag[len("!type:"):]
                    elif tag != "!:no-tag:" and not tag.startswith("tag:yaml.org,2002:"):
                        self.processing_functions[full_name] = tag[1:].split(",")

                    self.params[full_name] = self.resolve_node(yaml_loader, tag, node)
                    return self.params[full_name]

            else:
                if tag.lower() == "!type:config":
                    # If root of the YAML file but no provided name > assume dict
                    return yaml_loader.construct_mapping(node, deep=True)
                # If root of the YAML file and a name is provided > use first part as config name
                name = tag[1:]
                check_valid_param_name(name, f"Invalid name '{name}' found in file {self.path} : " + "{issue}.")

            with InSubConfig(self, name):
                value = yaml_loader.construct_mapping(node)

            return value

        loader = yaml.FullLoader
        if not hasattr(loader, "default_yaml_constructors"):
            loader.default_yaml_constructors = dict(loader.yaml_constructors)
            loader.yaml_constructors = {}
        loader.DEFAULT_MAPPING_TAG = "!type:config"
        loader.DEFAULT_SCALAR_TAG = "!:no-tag:"
        loader.DEFAULT_SEQUENCE_TAG = "!:no-tag:"
        yaml.add_multi_constructor("", generic_constructor, Loader=loader)

        return loader


def check_valid_param_name(name: str, message: Optional[str] = None) -> None:
    """ Raise relevant errors in the input name is not a valid sub-config name. """
    issue = None
    if not name:
        issue = "sub-config names cannot be empty"
    if not re.match(r'^[A-Za-z_*]', name):
        issue = "sub-config names must start with a letter or an underscore"
    if not re.match(r'^[A-Za-z0-9._*]*$', name):
        issue = "sub-config names can only contain letters, numbers, dots and underscores"
    if name.endswith('.'):
        issue = "sub-config names cannot end with a dot"
    if issue:
        raise ValueError(message.format_map({"issue": issue}))


class NoTag:
    """ Context manager to temporarily set the default mapping of a loader to "!:no-tag:" """

    def __init__(self, loader):
        self.loader = loader
        self.saved_default_mapping_tag = None

    def __enter__(self):
        self.saved_default_mapping_tag = self.loader.DEFAULT_MAPPING_TAG
        self.loader.DEFAULT_MAPPING_TAG = "!:no-tag:"

    def __exit__(self, *args):
        self.loader.DEFAULT_MAPPING_TAG = self.saved_default_mapping_tag


class InSubConfig:
    """ Context manager to temporarily append a name to the currently processed path. """

    def __init__(self, scanner, name):
        self.scanner = scanner
        self.name = name

    def __enter__(self):
        self.scanner.state["currently_processed_path"].append(self.name)

    def __exit__(self, *args):
        self.scanner.state["currently_processed_path"].pop(-1)
