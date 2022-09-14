"""
Reactive Reality Machine Learning Config System - ConfigHistory object
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

import glob
import importlib
import io
import os
import sys
import time
from functools import partial
from pathlib import Path

try:
    import pygraphviz as pgv
except ImportError:
    pass

from .config import Configuration


class ConfigHistory:
    """Configuration history manager."""

    def __init__(self, folder_path, config_filters=None,
                 difference_processor=None, ignore_for_graphing=None,
                 add_relevant_edges=False, tolerance=0, group_by=None,
                 metrics=None, display_span=False, config_class=Configuration):
        if not importlib.util.find_spec("pygraphviz"):
            raise ImportError("ConfigHistory requires pygraphviz - "
                              "currently not installed!")
        self.difference_processor = self.make_processor(difference_processor)
        self.ignore_for_graphing = self.make_processor(ignore_for_graphing)
        self.group_by = group_by

        print("Loading configs...")
        if not isinstance(folder_path, dict):
            yaml_files = glob.glob(os.path.join(folder_path, "**/*.yaml"),
                                   recursive=True)
            self.paths = [
                file[:-len("_hierarchy.yaml")] + ".yaml" for file in yaml_files
                if file.endswith("_hierarchy.yaml")
            ]
            self.names = [
                self.get_experiment_name_from_file(file, folder_path)
                for file in self.paths
            ]
            self.folders = [("", folder_path)] * len(self.paths)
        else:
            self.paths = []
            self.names = []
            self.folders = []
            for i in folder_path:
                yaml_files = glob.glob(
                    os.path.join(folder_path[i], "**/*.yaml"), recursive=True)
                to_add = [
                    fil[:-len("_hierarchy.yaml")] + ".yaml"
                    for fil in yaml_files if fil.endswith("_hierarchy.yaml")
                ]
                self.paths += to_add
                self.folders += [(i, folder_path[i])] * len(to_add)
                self.names += [
                    self.get_experiment_name_from_file(fil, folder_path[i],
                                                       name=i)
                    for fil in to_add
                ]

        if config_filters is not None:
            if not isinstance(config_filters, list):
                config_filters = [config_filters]
            for filt in config_filters:
                good = [filt(i) for i in self.paths]
                self.paths = [
                    self.paths[i] for i in range(len(self.paths)) if good[i]
                ]
                self.names = [
                    self.names[i] for i in range(len(self.names)) if good[i]
                ]
                self.folders = [
                    self.folders[i] for i in range(len(self.folders))
                    if good[i]
                ]

        self.modification_times = [os.path.getmtime(fil) for fil in self.paths]
        self.configs = []
        for path in self.paths:
            try:
                sys.stdout = io.StringIO()
                self.configs.append(config_class.load_config(path))
                sys.stdout = sys.__stdout__
            except Exception as exception:
                sys.stdout = sys.__stdout__
                print(f"Error while loading config {path} : ", exception)
        for i, config in enumerate(self.configs):
            if config.get("_former_saving_time", None) is not None:
                modification_time = config._former_saving_time
                self.modification_times[i] = modification_time

        print(f"Successfully loaded {len(self.configs)} configs from folder(s)"
              f" {folder_path}. Analysing differences...")

        self.matrix = self.compute_difference_matrix()
        self.span = self.compute_span()
        self.similarity_matrix = [[
            len(
                self.ignore_for_graphing(list(self.matrix[row][col]), row, col,
                                         self))
            for col in range(len(self.matrix[row]))
        ] for row in range(len(self.matrix))]
        self.similarity_coefficients = [
            sum(row) for row in self.similarity_matrix
        ]
        self.metrics = self.compute_metrics(metrics)
        self.config_graph = pgv.AGraph(
            strict=True, directed=True,
            label=self.format_span() if display_span else "")
        self.compute_graph(add_relevant_edges=add_relevant_edges,
                           tolerance=tolerance)
        print("Config graph done !")

    def compute_span(self):
        span = {}
        for i, row in enumerate(self.matrix):
            for j, elem in enumerate(row):
                ignored = self.ignore_for_graphing(elem, i, j, self)
                for param in ignored:
                    if param[0] not in span:
                        span[param[0]] = [param[1]]
                    elif param[1] not in span[param[0]]:
                        span[param[0]].append(param[1])
        return span

    def compute_metrics(self, metrics):
        if metrics is None:
            return {}
        if (isinstance(metrics, (list, tuple)) and all(
                isinstance(i, (list, tuple)) and len(i) in [2, 3]
                for i in metrics)):
            pass
        elif isinstance(metrics, (list, tuple)) and len(metrics) in [2, 3]:
            metrics = [metrics]
        else:
            raise Exception(f"Unrecognized format for metric {metrics}.")
        to_return = {}
        folder_paths = [Path(i).parents[0] for i in self.paths]
        for metric in metrics:
            try:
                metric_value = metric[1](folder_paths)
            except Exception as exception:
                print("There was an error parsing metrics : ", exception)
                raise exception
            if len(metric) == 2:
                to_return[metric[0]] = (metric_value, "")
            else:
                to_return[metric[0]] = (metric_value, metric[2])
        return to_return

    def compute_graph(self, add_relevant_edges=False, tolerance=0):

        def add_directed_edge(first, second):
            if (self.modification_times[first] >
                    self.modification_times[second]):
                self.config_graph.add_edge(
                    second, first, labeljust="l",
                    label=self.format_list(self.matrix[second][first]))
            else:
                self.config_graph.add_edge(
                    first, second, labeljust="l",
                    label=self.format_list(self.matrix[first][second]))

        potential_nodes = list(range(len(self.configs)))
        potential_nodes.sort(key=lambda x: self.modification_times[x])
        potential_nodes.sort(key=lambda x: self.similarity_coefficients[x])
        nodes_added = []
        for _ in range(len(potential_nodes)):
            if not nodes_added:
                index = potential_nodes.pop(0)
                nodes_added.append(index)
                self.config_graph.add_node(
                    index, style="filled", label=(
                        f"{self.names[index]}\n"
                        f"Date : {time.ctime(self.modification_times[index])}"
                        f"{self.format_metrics(index)}"))
            else:
                # Find which node to add in priority
                nodes_by_connectivity = nodes_added.copy()
                nodes_by_connectivity.sort(
                    key=lambda x: -self.modification_times[x])
                nodes_by_connectivity.sort(
                    key=lambda x: self.similarity_coefficients[x])

                relevant_similarities = [[
                    (self.similarity_matrix[i][j] if j in potential_nodes else
                     max(self.similarity_matrix[i]) + 1)
                    for j in range(len(self.similarity_matrix[i]))
                ] for i in nodes_by_connectivity]
                best_new_node = [min(i) for i in relevant_similarities]
                new_parent_node = nodes_by_connectivity[best_new_node.index(
                    min(best_new_node))]
                potential_new_nodes = [
                    i for i in potential_nodes
                    if (self.similarity_matrix[new_parent_node][i] == min(
                        best_new_node))
                ]
                potential_new_nodes.sort(
                    key=lambda x: self.modification_times[x])
                potential_new_nodes.sort(
                    key=lambda x: self.similarity_coefficients[x])
                new_node = potential_nodes.pop(
                    potential_nodes.index(potential_new_nodes[0]))
                # Add the node
                nodes_added.append(new_node)
                date = time.ctime(self.modification_times[new_node])
                self.config_graph.add_node(
                    new_node, style="filled",
                    label=(f"{self.names[new_node]}\n"
                           f"Date : {date}"
                           f"{self.format_metrics(new_node)}"))
                add_directed_edge(new_parent_node, new_node)

        if self.group_by is not None:
            if isinstance(self.group_by, str):
                self.group_by = [self.group_by]
            groups = {}
            for i, config in enumerate(self.configs):
                group = ""
                for j in self.group_by:
                    params = config.get_parameter_names()
                    for param in params:
                        if param.endswith("." + j) or param == j:
                            group += (f" ; {j}:{config[param]}"
                                      if group else f"{j}:{config[param]}")
                if group and group not in groups:
                    groups[group] = [i]
                elif group:
                    groups[group].append(i)
            for group, subgraph in groups.items():
                self.config_graph.add_subgraph(subgraph,
                                               name="cluster_" + group,
                                               label="\n" + group + "\n")

        if add_relevant_edges:
            relevant_similarities = [[
                len(self.matrix[i][j]) if j != i else max(
                    len(self.matrix[i][k])
                    for k in range(len(self.matrix[i]))) + 1
                for j in range(len(self.similarity_matrix[i]))
            ] for i in range(len(self.similarity_matrix))]
            for i, similarities in enumerate(relevant_similarities):
                minimum = min(similarities)
                for j, sim in enumerate(similarities):
                    if sim - minimum < tolerance + 1:
                        if not ((i, j) in self.config_graph.edges() or
                                (i, j) in self.config_graph.edges()):
                            add_directed_edge(i, j)

    def compute_colors(self, scheme="date", fill="top", legend=True,
                       base_color="white", class_scheme="/set312/",
                       number_scheme="/blues9/"):
        to_remove = []

        # Remove previous legend
        for i in self.config_graph.nodes():
            if "legend" in str(i):
                to_remove.append(i)
        for i in to_remove:
            self.config_graph.remove_node(i)

        # Determine colouring scheme
        unavailable = []
        if scheme == "date":
            indexes_values = list(
                zip(list(range(len(self.configs))), self.modification_times))
            indexes_values.sort(key=lambda x: x[1])
            color_scheme = number_scheme
        elif scheme.startswith("metric:"):
            if scheme[7:] not in self.metrics:
                raise Exception(f"Unknown metric : {scheme[7:]}.")
            indexes_values = list(
                zip(list(range(len(self.configs))),
                    self.metrics[scheme[7:]][0]))
            for indexes_value in indexes_values:
                if indexes_value[1] is None:
                    unavailable.append((indexes_value[0], None))
            indexes_values = [
                index for index in indexes_values
                if index[0] not in [i[0] for i in unavailable]
            ]
            if all(
                    isinstance(x[1], (int,
                                      float)) and not isinstance(x[1], bool)
                    for x in indexes_values):
                indexes_values.sort(key=lambda x: x[1])
                color_scheme = number_scheme
            else:
                color_scheme = class_scheme
        elif scheme.startswith("param:"):
            values = []
            for config in self.configs:
                found = False
                params = config.get_parameter_names()
                for param in params:
                    if param.endswith("." + scheme[6:]) or param == scheme[6:]:
                        if not found:
                            values.append(config[param])
                            found = True
                        else:
                            raise Exception(f"Ambiguous param : {scheme[6:]}.")
                if not found:
                    raise Exception(f"Unknown param : {scheme[6:]}.")
            indexes_values = list(zip(list(range(len(self.configs))), values))
            for indexes_value in indexes_values:
                if indexes_value[1] is None:
                    unavailable.append((indexes_value[0], None))
            indexes_values = [
                index for index in indexes_values
                if index[0] not in [i[0] for i in unavailable]
            ]
            if all(
                    isinstance(x[1], (int,
                                      float)) and not isinstance(x[1], bool)
                    for x in indexes_values):
                indexes_values.sort(key=lambda x: x[1])
                color_scheme = number_scheme
            else:
                color_scheme = class_scheme
        else:
            raise Exception(f"Unrecognized coloring scheme : {scheme}.")
        value_set = list({x[1] for x in indexes_values})
        if color_scheme == number_scheme:
            value_set.sort()
            color_set = [5]
            if fill == "top":
                for _ in range(len(value_set) - 1):
                    color_set = [max([0, min(color_set) - 1])] + color_set
            elif fill == "bottom":
                for _ in range(len(value_set) - 1):
                    color_set += [max([0, min(color_set) - 1])]
            elif fill == "full":
                factor = 6. / float(len(value_set))
                acc = 6 - factor
                for _ in range(len(value_set) - 1):
                    color_set = [max([0, int(acc // 1)])] + color_set
                    acc -= factor
            else:
                raise Exception(f"Unrecognized fill value : {fill}. "
                                "Please use 'top', 'bottom' or 'full'.")
        else:
            color_set = [x % 13 for x in range(len(value_set))]
        one_is_colored = False
        for i in self.config_graph.nodes():
            if "legend" not in str(i):
                value = None
                for index_value in indexes_values:
                    if index_value[0] == int(str(i)):
                        value = index_value[1]
                if value is not None:
                    color = color_set[value_set.index(value)]
                    is_none = False
                    for index_value in unavailable:
                        if index_value[0] == int(str(i)):
                            is_none = True
                            i.attr["fillcolor"] = "gray91"
                    if not is_none:
                        one_is_colored = True
                        i.attr["fillcolor"] = (color_scheme + str(color)
                                               if color else base_color)
                else:
                    i.attr["fillcolor"] = "gray91"
        if legend and one_is_colored:
            legend_nodes = []
            for i in range(6 if color_scheme ==
                           number_scheme else len(value_set)):
                if color_scheme == number_scheme:
                    values = [
                        value_set[v] for v in range(len(value_set))
                        if color_set[v] == i
                    ]
                    if not values:
                        label = None
                    elif len(values) == 1:
                        if isinstance(values[0], float) and scheme != 'date':
                            label = f"{values[0]:.3f}"
                        else:
                            label = str(values[0] if scheme != 'date' else time
                                        .ctime(values[0]))
                    else:
                        if isinstance(values[0], float) and scheme != 'date':
                            label = f"[{min(values):.3f} ; {max(values):.3f}]"
                        else:
                            label = ("[" + str(
                                min(values) if scheme != 'date' else time
                                .ctime(min(values))) + " ; " + str(
                                    max(values) if scheme != 'date' else time
                                    .ctime(max(values))) + "]")
                else:
                    if i not in color_set:
                        label = None
                    else:
                        label = ""
                        for j, val in enumerate(value_set):
                            label += f"{val}\n" if color_set[j] == i else ""
                if label is not None:
                    legend_nodes.append("legend_" + str(i))
                    self.config_graph.add_node(
                        "legend_" + str(i), label=label, style="filled",
                        fillcolor=color_scheme + str(i) if i else base_color)
            self.config_graph.add_subgraph(legend_nodes, name="cluster_legend",
                                           label=f"Legend for {scheme}")
            for i in legend_nodes:
                self.config_graph.add_edge(
                    self.modification_times.index(max(
                        self.modification_times)), i, style="invis")

    def draw_graph(self, path="graph.png", scheme="date", fill="top",
                   legend=True):
        self.compute_colors(scheme=scheme, fill=fill, legend=legend)
        self.config_graph.layout(prog="dot")
        self.config_graph.draw(path)
        print("Config graph saved !")

    def format_metrics(self, index):
        string = ""
        for i, metric in self.metrics.items():
            if metric[0][index] is None:
                string += f"\n{i} : UNAVAILABLE"
            elif isinstance(metric[0][index], float):
                string += f"\n{i} : {metric[0][index]:.3f} {metric[1]}"
            else:
                string += f"\n{i} : {metric[0][index]} {metric[1]}"
        return string

    def format_span(self):
        string = "\nExploration span\n\n"
        for i, val in self.span.items():
            string += f"{i} : {val}" + r"\l"
        return string

    def compute_difference_matrix(self):
        matrix = []
        similars = []
        for i, config_i in enumerate(self.configs):
            row = []
            similar = [i]
            for j, config_j in enumerate(self.configs):
                if j != i:
                    differences = config_i.compare(config_j, reduce=True)
                    row.append(
                        self.difference_processor(differences, i, j, self))
                    if not row[-1]:
                        similar.append(j)
                else:
                    row.append([])
            if all(similar[0] not in k for k in similars):
                similars.append(similar)
            matrix.append(row)
        fuse = []
        for i in similars:
            if len(i) > 1:
                dates = [
                    self.modification_times[j] if j in i else 0
                    for j in range(len(self.modification_times))
                ]
                key_func = partial(lambda x, dates: dates[x], dates=dates)
                sort = sorted(i, key=key_func, reverse=True)
                for j in sort:
                    if j != dates.index(max(dates)):
                        self.names[dates.index(max(dates))] = (
                            f"({self.names[j]})\n"
                            + self.names[dates.index(max(dates))])
                fuse += [j for j in i if j != dates.index(max(dates))]
        self.names = [
            self.names[i] for i in range(len(self.names)) if i not in fuse
        ]
        self.configs = [
            self.configs[i] for i in range(len(self.configs)) if i not in fuse
        ]
        self.paths = [
            self.paths[i] for i in range(len(self.paths)) if i not in fuse
        ]
        self.modification_times = [
            self.modification_times[i]
            for i in range(len(self.modification_times)) if i not in fuse
        ]
        matrix = [[
            matrix[i][j] for j in range(len(matrix[i])) if j not in fuse
        ] for i in range(len(matrix)) if i not in fuse]
        return matrix

    @staticmethod
    def get_experiment_name_from_file(file, folder, name=None):
        file_parent_minus_folder = os.path.relpath(
            Path(file).parents[0], os.path.commonpath([folder,
                                                       file])).strip("/_")
        if name is None:
            return file_parent_minus_folder
        return f"{name}:{file_parent_minus_folder}"

    @staticmethod
    def format_list(list_to_format):
        string = " "
        for i in list_to_format:
            string += str(i[0]) + " : " + str(i[1]) + r"\l "
        return string

    @staticmethod
    def make_processor(argument):

        def apply_list(list_to_apply, inp, *args):
            for func in list_to_apply:
                inp = func(inp, *args)
            return inp

        if argument is None:
            return lambda d, i, j, h: d
        if not isinstance(argument, list):
            return argument
        return lambda d, i, j, h: apply_list(argument, d, i, j, h)
