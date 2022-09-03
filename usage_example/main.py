"""
Reactive Reality Machine Learning Config System - Usage example (main file)
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

import json
import os

from configs.project_config import ProjectSpecificConfiguration
from project_utils.utils import (create_and_train_model, create_data,
                                 log_experiment, test_model_and_return_metrics)

from yaecs import ConfigHistory


def perform_experiment(config_path):
    config = ProjectSpecificConfiguration.load_config(config_path)

    for _ in range(config.number_of_repeats):
        if config.get_config_variations():
            variations = config.get_config_variations()
        else:
            variations = [config]
        for variation in variations:
            train, test = create_data(variation.data)
            model = create_and_train_model(variation.model, train)
            computed_metrics = test_model_and_return_metrics(
                model, test, variation.metrics)
            log_experiment(variation, computed_metrics)


if __name__ == "__main__":
    if "log" not in os.listdir():
        # Perform random search
        print("\nStep 0 : performing dummy test")
        perform_experiment("./configs/experiment/dummy_test.yaml")

        # Perform random search
        print("\nStep 1 : performing random search")
        perform_experiment("./configs/experiment/random_search.yaml")

        # Perform grid search
        print("\nStep 2 : performing grid search")
        perform_experiment("./configs/experiment/grid_search.yaml")

    # Build config graphs
    # First let's build the graph of all the experiments. We want to filter
    # out the dummy_test, so we'll include a config filter. A config filter is
    # a function which takes a path as argument and returns whether the
    # experiment corresponding to this path should appear in the graph
    # (True/False).

    def config_filter(path):
        return "dummy_test" not in path

    history = ConfigHistory("log", config_filters=config_filter,
                            config_class=ProjectSpecificConfiguration)
    history.draw_graph("all_experiments.png")

    # It's a big mess, isn't it ? Let's improve it step by step :)
    # First, we should remove the parameter names which we
    # don't care about : type_variation, param1_variation,
    # param2_variation, param3_variation, grid and number_of_repeats.
    # This can be done by processing the differences between configs
    # with a difference_processor. A difference_processor is a function
    # which takes the list of all differences, the index of the
    # reference config, the index of the compared config, and the
    # history object itself. It returns the new list of differences.
    # The three last arguments are here to provide information to use
    # during processing. We don't need them in our case. Since the
    # difference list contains ("name", difference) tuples, we just
    # need to access the names for our purpose.

    def difference_processor(difference, reference_index, compared_index,
                             hist):
        # NOTE we don't use all the arguments here but they are required
        # by ConfigHistory
        # pylint: disable=unused-argument
        return [
            d for d in difference if d[0] not in [
                "type_variation", "param1_variation", "param2_variation",
                "param3_variation", "grid", "number_of_repeats"
            ]
        ]

    history = ConfigHistory("log", config_filters=config_filter,
                            config_class=ProjectSpecificConfiguration,
                            difference_processor=difference_processor)
    history.draw_graph("all_experiments_processed_differences.png")

    # But there's still way too many nodes here, and just removing the
    # dummy run did not help much.
    # Let's have a look at the random search and the grid search
    # separately.

    history = ConfigHistory("log/random_search", config_filters=config_filter,
                            config_class=ProjectSpecificConfiguration,
                            difference_processor=difference_processor)
    history.draw_graph("random_search_processed_differences.png")
    history = ConfigHistory("log/grid_search", config_filters=config_filter,
                            add_relevant_edges=True,
                            config_class=ProjectSpecificConfiguration,
                            difference_processor=difference_processor)
    history.draw_graph("grid_search_processed_differences.png")

    # This already looks much easier to parse ! But the colors are
    # useless, because we have performed all those experiments at the
    # same time and the graph is colored by date. We would like to
    # color the graph with respect to our metrics. First, let's implement
    # the metrics. The metrics is a list of ("name", function) tuple, where
    # the function takes the path to an experiment and reads the corresponding
    # metric value from the folder.
    def get_metric(paths, key_name):
        res = []
        for path in paths:
            with open(os.path.join(path, "metrics.json"), "r",
                      encoding="utf-8") as fil:
                res.append(json.load(fil)[key_name])
        return res

    metrics = [
        ("exponential_l2", lambda paths: get_metric(paths, 'is_exponential')),
        ("square_root_l2", lambda paths: get_metric(paths, 'is_square_root'))
    ]

    random_hist = ConfigHistory("log/random_search",
                                config_filters=config_filter, metrics=metrics,
                                config_class=ProjectSpecificConfiguration,
                                difference_processor=difference_processor)
    grid_hist = ConfigHistory("log/grid_search", config_filters=config_filter,
                              metrics=metrics, add_relevant_edges=True,
                              config_class=ProjectSpecificConfiguration,
                              difference_processor=difference_processor)

    # We can now draw the graphs using the metrics as a way to color.
    # By default (fill="top"), the colors are applied only to the configs
    # where the value is the highest. In our case, we want to color all node
    # so we'll use fill="full", where the whitest nodes are the best.

    random_hist.draw_graph("random_search_exp_colour.png",
                           scheme="metric:exponential_l2", fill="full")
    random_hist.draw_graph("random_search_sqrt_colour.png",
                           scheme="metric:square_root_l2", fill="full")
    grid_hist.draw_graph("grid_search_exp_colour.png",
                         scheme="metric:exponential_l2", fill="full")
    grid_hist.draw_graph("grid_search_sqrt_colour.png",
                         scheme="metric:square_root_l2", fill="full")

    # Finally, it can be very interesting to study the effect of a given
    # parameter on the metrics. One way to do this is to group the graph by
    # groups where this parameter takes the same value.

    history = ConfigHistory("log/random_search", config_filters=config_filter,
                            metrics=metrics, group_by=["type"],
                            config_class=ProjectSpecificConfiguration,
                            difference_processor=difference_processor)
    history.draw_graph("random_search_exp_by_type.png",
                       scheme="metric:exponential_l2", fill="full")
    history.draw_graph("random_search_sqrt_by_type.png",
                       scheme="metric:square_root_l2", fill="full")

    # On these graphs, it seems that a polynomial model is always better,
    # w.r.t. "exp" or "sqrt". This is why the grid search is performed with
    # a polynomial model.

    history = ConfigHistory("log/grid_search", config_filters=config_filter,
                            metrics=metrics, group_by=["param1"],
                            add_relevant_edges=True,
                            config_class=ProjectSpecificConfiguration,
                            difference_processor=difference_processor)
    history.draw_graph("grid_search_exp_by_param1.png",
                       scheme="metric:exponential_l2", fill="full")
    history.draw_graph("grid_search_sqrt_by_param1.png",
                       scheme="metric:square_root_l2", fill="full")
    history = ConfigHistory("log/grid_search", config_filters=config_filter,
                            metrics=metrics, group_by=["param2"],
                            add_relevant_edges=True,
                            config_class=ProjectSpecificConfiguration,
                            difference_processor=difference_processor)
    history.draw_graph("grid_search_exp_by_param2.png",
                       scheme="metric:exponential_l2", fill="full")
    history.draw_graph("grid_search_sqrt_by_param2.png",
                       scheme="metric:square_root_l2", fill="full")
    history = ConfigHistory("log/grid_search", config_filters=config_filter,
                            metrics=metrics, group_by=["param3"],
                            add_relevant_edges=True,
                            config_class=ProjectSpecificConfiguration,
                            difference_processor=difference_processor)
    history.draw_graph("grid_search_exp_by_param3.png",
                       scheme="metric:exponential_l2", fill="full")
    history.draw_graph("grid_search_sqrt_by_param3.png",
                       scheme="metric:square_root_l2", fill="full")

    # Looking at those graphs makes it easy to see that, for each metric,
    # there is a value of the studied parameter which is ALWAYS better.
    # For instance, note how in grid_search_exp_by_param1.png, following an
    # arrow from a node in the param1:0.5 group to its counterpart in the
    # param1:1 group always makes the color go lighter.
