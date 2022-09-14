# YAECS (Yet Another Experiment Config System) : documentation

---

This documentation page describes our Config System. This configuration handler
object is meant to make some operations more practical, including :

- printing, saving and loading configurations easily and in a flexible way
- flexibility to adapt to the size of a project (simple configs for small
projects, multi-file and/or nested configs for large projects)
- making it easy to change the config between two experiments, to implement
hyper-parameter searches, or to visualise the differences between past
experiments
- increasing the overall readability of the config files and introducing
safeguards against bad practices for projects with several contributors/use
cases
- allowing for every single parameter in a project to be grouped in a single
place (the default config) for easy access, without making the config hard to
manipulate and use due to its size

## I) Getting started

Using configurations in your project includes two main steps : creating the
config files, then loading them. You can then use your configs as you see fit.

### Creating basic config files

A project will typically use two kinds of config files : the “default” config
and the “experiment” configs.

The “default” config is the basic configuration of your project. **All the
parameters that could possibly be used in your project should be defined in
the default config**. This config file should be saved as a YAML file somewhere
on your disk, for example at `path/to/default_config.yaml`. Here is an example
default config :

```yaml
--- # Default config example
network_layers: 5
dataset_version: "1.0"
train_val_test_splits: [0.8, 0.1, 0.1]
learning_rate: 0.1
a_value_that_is_useful_somewhere_but_will_never_change: 42
output_directory: ""
```

We can then create as many “experiment” configs as we want. For example, such
a file saved at `path/to/experiment_config_1.yaml` would be a valid experiment
config :

```yaml
--- # Experiment config
output_directory: "./exp1"
dataset_version: "1.4"
learning_rate: 0.05
```

As you can see, you don’t need to set everything in the experiment config.
You can focus on what changes and what is relevant to the current experiment.
However, you can only set parameters that exist in the default config.

### Loading your config files

Your config files can now be loaded. To load the config files, you will need a
config handler specific to your project. The base config handler is a class,
called `Configuration`, which would be located in the framework. Every project
should define a child of this class as follows :

```python
from yaecs import Configuration

class ProjectConfiguration(Configuration):
    @staticmethod
    def get_default_config_path():
        return "path/to/default_config.yaml"

    def parameters_pre_processing(self):
        return {}
```

This allows you to define two variables specific to your project : the path to
the default config file (which will then never change), and the set of
pre-processing functions that you will want to use for your parameters (see
_“Advanced features : Pre-processing”, “Advanced features : Splitting across
several files” and “Advanced features : Defining variations for a config”_).
**If those two elements are not set the config system will throw an error
when it is used**, which should make it obvious that something is missing.

Alternatively, if you have a small project and want to keep it very simple,
you can use our template class :

```python
from yaecs import get_template_class

ProjectConfiguration = get_template_class(
    default_config_path="path/to/default_config.yaml"
)
```

You can now load your configuration. The default config will always be loaded
first, so we do not need to mention it again :

```python
config = ProjectConfiguration.load_config("path/to/experiment_config_1.yaml")
print(config.details())

# Print output :
# MAIN CONFIG :
# Configuration hierarchy :
# > ./configs/test/default_config.yaml
# > path/to/experiment_config_1.yaml
#
#  - network_layers : 5
#  - dataset_version : 1.4
#  - train_val_test_splits : [0.8, 0.1, 0.1]
#  - learning_rate : 0.05
#  - a_value_that_is_useful_somewhere_but_will_never_change : 42
#  - output_directory : ./exp1
```

You can then call any parameter like you would an attribute of this object.
For example, the number of layers would be `config.network_layers`, or the
dataset version would be `config.dataset_version`. Accessing parameters can
also be done using conventional dictionary operations, for instance
`config["network_layers"]` or `config.get("network_layers")` would work.

NB : if you want to create a config with no defaults, for example from a
dictionary (in a short script or in a jupyter notebook for instance), you can
simply use `make_config(dict)`. The `make_config` function is the fastest,
simplest way to create a bare-bone Configuration object out of a native python
object. It uses a template Configuration subclass to create a config object
with no defaults and no processing.

### Simple usage examples

#### Running experiments

Suppose that you want to test several values for `learning_rate` in the example
above. You know that most of your experiments for a while are going to use the
dataset 1.4, the same network and splits, so you keep all your previously
defined config files and then want to experiment with the learning rate only.
The following code would allow you to do this.

```python
learning_rates = [0.1, 0.01, 0.001]

for i in learning_rates:
    config = ProjectConfiguration.load_config(
        "path/to/experiment_config_1.yaml"
    )
    config.merge({"learning_rate": i})
    run_experiment(config)
    config.save(os.path.join(config.output_directory,
                             "lr{}_config.yaml".format(i)))
```

There you have it, that’s all it takes !

What happens here is that the `load_config()` function first loads the default
config (as always), and then merges your general config
`"path/to/experiment_config_1.yaml"` into it (as in the first example). Then,
you manually merge your experiment-specific config into your config. As you
can see, configs can be merged from a path to a YAML file or from a dictionary.

As it so happens, the `load_config()` function also calls `merge()` internally
(because it needs to merge `path/to/experiment_config_1.yaml` into the default
config), and can merge several configs consecutively if you feed it a list of
configs. Therefore, a code equivalent to the one above would be :

```python
learning_rates = [0.1, 0.01, 0.001]

for i in learning_rates:
  config = ProjectConfiguration.load_config([
    "path/to/experiment_config_1.yaml", {"learning_rate": i}
  ])
  run_experiment(config)
  config.save(os.path.join(config.output_directory,
                           "lr{}_config.yaml".format(i)))
```

You may be interested to not that both choosing which experiment config to load
AND overwriting parameters can of course also be done from the command line if
you don't want to edit the code itself. Find out more about this in
_“Advanced features : Using the command line support”_.

#### Comparing experiments

Suppose you performed three experiments with different learning rates, as in
the example above. Maybe it was a while ago, and you don’t exactly remember
what that experiment was about, or maybe your colleague performed those
experiments, and you’re not sure how they were done. Of course, you could just
check the saved config files inside the experiment folders, but those files
might contain quite a lot of information.

There is actually a very efficient way to check for differences. When a config
is saved, two file are created :
`<save_name>.yaml` and `<save_name>_hierarchy.yaml`. Let us have a look at
both files :

```yaml
config_metadata: 'Saving time : Mon Dec 20 09:46:51 2021 (1639990011.1963022) ; Regime : auto-save'
network_layers: 5
dataset_version: '1.4'
train_val_test_splits:
- 0.8
- 0.1
- 0.1
learning_rate: 0.1
a_value_that_is_useful_somewhere_but_will_never_change: 42
output_directory: ./exp1
```

```yaml
config_hierarchy:
- path/to/default_config.yaml
- path/to/experiment_config_1.yaml
- learning_rate: 0.1
```

As you can see, even with our very simple example things are starting to look
busy in there. The first file contains everything your code needs to know to
reproduce this experiment consistently. The first row contains general
metadata, for your and the config system’s use. It contains the date when the
config was saved both in float representation and in human-readable format.
As for `overwriting_regime`, it refers to an internal property of config
objects (see _“Advanced features : Changing the overwriting regime”_).

`config_hierarchy` however, which is the only element in the second file, is a
very useful overall view of what lead to the config used for this experiment.
It basically shows the configs, in the correct order, that were merged to
obtain the config of the experiment. Therefore, this shows us at a glance that
this experiment is an instance of the `path/to/experiment_config_1.yaml` config
where the learning rate was set to `0.1`. Technically speaking, the rest of
the information is then not needed because if those YAML files do not change,
you can always get this same configuration by building the same
`config_hierarchy`. We do however include the rest of the information in the
first file so that you can also access the state of any parameter easily, and
so that the experiment always remains reproducible even if the YAML files
change.

#### Reproducing experiments

Reproducing an experiment is as simple as loading the config file that was
saved when it was performed.

```python
config = ProjectConfiguration.load_config("./exp1/lr0.1_config.yaml")
run_experiment(config)
```

If you are careful with how you introduce new features and parameters, these
saved configs will always be forward-compatible. Suppose for instance that,
after running this experiment, you add the possibility for your network to have
squeeze-and-excitation layers. All you have to do is to add the corresponding
parameters in the default config in such a way that the default values have no
influence on the code. For instance, your new default_config could look like
this :

```yaml
--- # Default config example
network_layers: 5
dataset_version: "1.0"
train_val_test_splits: [0.8, 0.1, 0,1]
learning_rate: 0.1
a_value_that_is_useful_somewhere_but_will_never_change: 42
output_directory: ""
use_squeeze_excitation: false
```

Setting the `use_squeeze_excitation` to `false` by default means that running
the default parameters will start the exact same experiment as before
introducing this feature. Since the `use_squeeze_excitation` parameter does
not exist in the saved experiment config, it will not be merged, the false
default value will be conserved and the experiment will be identically
reproduced. You no longer need to update your old config files to use them ;).

You can just as easily introduce any new parameter in the default config
without having to update every single config in your config directory, without
having to edit your colleagues' config files, and without having to
systematically handle non-existing parameters in your code. All you need to do
is ensure that your new code with the default parameters has the same behaviour
as the old code.

It also makes it very easy to check what an earlier experiment would have
yielded if it had benefited from a newly implemented feature. For instance, we
can easily re-run the above-mentioned experiment with the new
squeeze-and-excitation modules.

```python
config = ProjectConfiguration.load_config("./exp1/lr0.1_config.yaml")
config.merge({"use_squeeze_excitation": True})
run_experiment(config)
```

## II) Advanced features

### Defining parameters pre-processing

It is rather frequent to want to pre-process your parameters before using them.
The Configuration object can handle this automatically. Here would be useful
use cases for this feature :

- process paths to make them relative paths/absolute paths, or raise errors if
they do not exist
- check if the values given to a parameter are valid (although this could be
done more easily with a function
being run on the entire config after the config creation, otherwise a check
function would need to be
defined for each parameter individually)
- transform angles from/to radians or similar conversions
- not make any change to the parameter, but perform an action when this
parameter is set, thus calling
the function (be careful when doing this, as the order in which those actions
are performed will become dependent on the order in which parameters are
processed)

**A pre-processing function needs to be a function that takes a single argument
(the parameter’s value) and returns the new value of the parameter.**

To define which pre-processing function should be applied to which parameter,
simply use the overridden `parameters_pre_processing` method of the
project-specific Configuration sub-class. In our first example, this was set to
return an empty dictionary. In this dictionary, you can define
`"parameter_name": function_to_apply` pairs to apply those functions to those
parameters. Here is an example :

```python
def parameters_pre_processing(self):
    return {
        "path_param": replace_relative_path_with_absolute,
        "path_list_param": lambda x: [replace_relative_path_with_absolute(path)
                                      for path in x],
        "critical_param": check_critical_param_value,
        "string_param": lambda x: x.upper(),
        "angle_param": convert_to_radians
    }
```

Of course, in the example above, you will need to have defined/imported the `replace_relative_path_with_absolute`, `check_critical_param_value` and
`convert_to_radians` functions. The `parameters_pre_processing()` function is
defined inside the Configuration class so that calling other methods of the
Configuration class with `self` is simple. This will come in very handy in the
next advanced use section : _Defining a config over several files_.

Referring to a parameter within a sub-config is done using the dot convention,
for example `sub_config_name.parameter_name`. The special character "*" is
also supported in parameter names as a replacement of any number of unknown
characters. For example, the following code will apply the
`sub_config_1_preproc` function to all parameters of the sub-config
`subconfig1`, and the `path_preproc` function to all parameters that end with
`_path`. If there is a parameter in `subconfig1` that also ends with `_path`,
both functions will be used in the order defined by the dictionary.

```python
def parameters_pre_processing(self):
    return {
        "subconfig1.*": sub_config_1_preproc,
        "*_path": path_preproc
    }
```

### Defining a config over several files

It can often be very useful to split your config into several files to access
the parameter you are looking for more efficiently. In combination with some
nice features of the YAML syntax, the Configuration class allows to organize
your config more efficiently.

#### 1. Several documents in a single file

The Configuration class supports being fed YAML files with several documents.
All documents are then concatenated together to create the config. As an
example, the following YAML file :

```yaml
--- # Document 1, defining for instance the network
network_layers: 5
number_of_filters: 4

--- # Document 2, defining for instance the data
dataset_version: "1.0"
```

would result in a config with three parameters : `config.network_layers`,
`config.number_of_filters` and `config.dataset_version`. This is an especially
useful if you split the default config (which is usually very big) into several
files with method 2., and then define a small experiment config to merge with
the default config. If the experiment config is small and changes a few
parameters per file, you probably want to keep it in a single file. But at the
same time, you may want to keep the file structure of the default config
visible. A good way to do that is to write each file of the default config as
a separate document in the experiment config. The YAML file above could for
example be the experiment config corresponding to the default config presented
in the next section.

#### 2. Several files defining a single config

As mentioned right before, defining all your parameter sections as documents
of a single file may end up creating a really long file, especially for the
default config. To avoid this, configs can be split into several files. The
main file (the one which will be called by the merge function) will then
contain some special parameters to indicate the paths to the other files to
the Configuration object. Here is an example :

```yaml
--- # Default config - main file (path : ./configs/default/main_config.yaml)
mode: "train" # train, test, infer
network_config_path: ./configs/default/network_config.yaml
data_config_path: ./configs/default/data_config.yaml
```

```yaml
--- # Default config - network file (path : ./configs/default/network_config.yaml)
network_layers: 5
number_of_filters: 4
```

```yaml
--- # Default config - data file (path : ./configs/default/data_config.yaml)
dataset_version: "1.0"
```

Of course, we now need a way to tell the Configuration object that
`network_config_path` and `data_config_path` are going to be paths that need to
be used to find the other files. As it turns out, we can reuse the
pre-processing feature to do just that : those paths will be pre-processed
such that their content is added
to the config. We just need to use the `register_as_additional_config_file`
method as pre-processing functions for those parameters :

```python
def parameters_pre_processing(self):
    return {
        "network_config_path": self.register_as_additional_config_file,
        "data_config_path": self.register_as_additional_config_file
    }
```

This would result in a config containing 6 parameters : `config.mode`,
`config.network_config_path`, `config.data_config_path`,
`config.network_layers`, `config.number_of_filters` and
`config.dataset_version`.

Please note that this is a good opportunity to use the capacity of
pre-processing dictionaries to support pattern-matching. For instance, a more
elegant way to write the above cell would be :

```python
def parameters_pre_processing(self):
    return {
        "*_config_path": self.register_as_additional_config_file
    }
```

This way, any param ending with “_config_path” anywhere in the config would be
interpreted as a path to a new config file.

### Defining nested configs

Another desirable property of our configuration is the ability to nest
configurations inside other configurations. Reusing the example of section 2.
of the previous advanced feature, it is easy to see that as the number of
parameters grows, it would be nice to not only organize those parameters in
different files on the disk, but also organize them in different “sub-configs”
in our Configuration object. That way, a function that requires access to
parameters of a certain nature can be passed only the parameters
relevant to this function.

Notifying the config that a certain subset of parameters needs to form a
sub-config of the current config can be done using yaml tags. A yaml tag
starts with “!” and is then followed by the name of the tag, for
example `!network_config`. The Configuration object uses two different
kinds of yaml tags :

- tags applying to an entire document. They are declared at the start of
the document, and all parameters defined in the same document will belong
to the declared sub-config
- tags applying to a dictionary parameter. They are declared after the name
of the parameter, and all parameters defined in the dictionary will belong to
the declared sub-config

Sounds confusing ? Let’s have a look at an example :

```yaml
--- # Default config - main file (path : ./configs/default/main_config.yaml)
mode: "train" # train, test, infer
data_config_path: ./configs/default/data_config.yaml

--- !network
network_layers: 5
number_of_filters: 4
```

```yaml
--- !data # Default config - data file (path : ./configs/default/data_config.yaml)
dataset_version: "1.0"
data_split: !data_split
    train: 0.8
    val: 0.1
    test: 0.1
```

Here is a default config that uses all the advanced features we have seen so
far. It is defined over two files (assuming the proper pre-processing function
is set for the `data_config_path` parameter), and uses configuration nesting
to add some structure to the config definition. We can see that it uses twice
the tag declaration at the start of a document (`!network` and `!data`), and
once the tag declaration as a dictionary inside a parameter (`!data_split`).

This will create the following structure :

- `config` is the main config, called “main” (the config name is used mostly
when printing the config). It contains 4 parameters : `config.mode`,
`config.data_config_path`, `config.network` and `config.data`. The parameters
`config.network` and `config.data` are named according to the YAML tags.

- `config.network` is also an instance of the Configuration class. Its name is
“network” and it contains two parameters : `config.network.network_layers` and
`config.network.number_of_filters`.

- Finally, `config.data` is also an instance of the Configuration class,
named “data”. It contains two parameters : `config.data.dataset_version` and
`config.data.data_split`. And of course, `config.data.data_split` is itself a
sub-config of the sub-config `config.data`, with the name “data_split” and the
three parameters `config.data.data_split.train`, `config.data.data_split.val`
and `config.data.data_split.test`.

To overwrite a parameter in a sub-config, the same sub-config must be defined
in the experiment config. For example, if I want to change the splits to
`[0.9, 0.1, 0.0]`, then a minimal experiment config would look like this :

```yaml
--- !data
data_split: !data_split
    train: 0.9
    test: 0.0
```

Again, you may use “.” and “*” in your experiment configs to access members of
sub-configs more efficiently or more clearly. For example, the following two
cells would be equivalent to the last cell and constitute a valid experiment
config :

```yaml
data.data_split.train: 0.9
data.data_split.test: 0.0
```

```yaml
"*.train": 0.9
"*.test": 0.0
```

As you can probably guess, though the example using “.” looks pretty good and
readable, using the example with “\*” is probably a bad idea. Indeed, this
makes things less readable as it becomes unclear what exactly is
being set. Moreover, the above experiment config would look in the whole config
for all parameters in all sub-config following the “\*.train” pattern, which
could result in unexpected matches. To clarify this behaviour, and since pattern
matching like this can actually come in very handy in certain situations,
a warning will be displayed each time a pattern param is merged, specifying the
full path of all the params that were matched by this pattern. This way, you
can (and should !) check in your logs if your pattern had the intended effect.

Did you note the double-quotes around the starred parameters in the YAML file ?
Those are mandatory because the star character has another meaning in yaml
(look up YAML anchors for more info). The quotes ensure that YAML understands
those stars to be verbatim parts of parameter names.

### Defining variations for a config

Suppose you want to make a GridSearch, or to at least test several values of a
single parameter. One way to do it would be like we presented in the basic
examples :

```python
search = [{"learning_rate" : i} for i in [0.1, 0.01, 0.001]]

for exp_config in search:
  config = ProjectConfiguration.load_config([
    "path/to/experiment_config_1.yaml", exp_config
  ])
  run_experiment(config)
  config.save(os.path.join(config.output_directory,
                           f"lr{exp_config['learning_rate']}_config.yaml"))
```

Now, with only three files to go through to check the differences between
configs, this may be usable. However, what would happen if you designed a
short experiment and ran it for hundreds of different values ? This would
create hundreds of files to go through and check if you wanted to check out
what this search was about. The config variations feature allows you to define
within your config file how this config will vary, and to automatically create
all the variations of your config. That way, you only need to save the parent
config and go through it to get a quick overview of all the children that have
been generated during your parameter search.

#### Basic usage

Let’s go through an example to see how to define variations and how to use
them. The final product that we expect to get is a list of children configs
that are variations of a parent config. This means that all we need to do is
specify the list of changes from the parent to the children.

```yaml
--- # Experiment config
learning_rate: 0.1
number_of_layers: 5
number_of_filters: 4

variations:
  - learning_rate: 0.1
  - learning_rate: 0.01
  - learning_rate: 0.001
```

```python
def parameters_pre_processing(self):
    return {
        "variations": self.register_as_config_variations
    }
```

```python
config = ProjectConfiguration.load_config("path/to/experiment_config_1.yaml")
config.save(os.path.join(config.output_directory, "config.yaml"))

for exp_config in config.create_variations():
  run_experiment(exp_config)
```

Here, we first defined some possible variations. The `variations` parameter is
a list because we want several variations to take place consecutively, and each
element of the list is a merge-able config (either a dict or a path to a yaml
file, in this case we have a dict that contain only the `learning_rate`
parameter).

We then register the `variations` parameter as a config variations list.

Finally, we call `config.create_variations()`, which will create copies of the
parent list and merge the variations into those copies to return the list of
children configs. We now only need to save the parent config because finding
the children from the parent is fully determined by the content of the parent.
Additionally, it is easy to visualise the entirety of the set of experiments
just by having a look at the `variations` parameter.

#### Advanced usage

Variations do not need to be defined all at once. They can be defined across
several parameters as long as those parameters are all defined in the main root
config file and registered using `self.register_as_config_variations`. They can
also refer to parameters in other sub-configs as long as all the variation
parameters are defined in the root config. For instance, the following config :

```yaml
--- # Experiment config
learning_rate: 0.1
network_config_path: path/to/network_config.yaml

lr_variations:
  - learning_rate: 0.1
  - learning_rate: 0.01
filter_variations:
  - network.number_of_filters: 4
  - network.number_of_filters: 5
  - network.number_of_filters: 6

--- !network # Network config
number_of_layers: 5
number_of_filters: 4
```

will result in 5 configs being produced, where two will vary the learning rate
only and three will vary the number of filters only.

Now you may be wondering, is it possible to have the different variations
parameters interact to create a grid for a GridSearch ? Yes it is ! However,
to do that we need to tell the Configuration object that some variations are
meant to interact. To do this, we will use a parameter that lists the
variations that need to form a grid, then register this parameter as a grid
using the `self.register_as_grid` method.

```yaml
--- # Experiment config
learning_rate: 0.1
number_of_layers: 5
number_of_filters: 4

lr_variations:
  - learning_rate: 0.1
  - learning_rate: 0.01
layers_variations:
  - number_of_layers: 5
  - number_of_layers: 6
lr_layer_grid_search: [lr_variations, layers_variations]
filter_variations:
  - number_of_filters: 4
  - number_of_filters: 5
```

```python
def parameters_pre_processing(self):
    return {
        "*_variations": self.register_as_config_variations,
        "*_grid_search": self.register_as_grid
    }
```

The above configuration will create 6 children : the first four will be a grid
between the different possible learning rate values and the different possible
numbers of layers (using the default number of filters), and the last two will
be an experiment where only the number of filters will vary (using the default
learning rate and the default number of layers). You can of course define as
many variations and grids as you want to, and they will all be performed
consecutively.

### Using the command line support

#### Choosing the experiment config from the command line

If you do not want to change your main code constantly to update the name of
your latest experiment config, we have something ready for you ! You can
actually set this from the command line. The python code to get the experiment
config path from the command line and load it looks like this :

```python
config = ProjectConfiguration.build_from_argv(
    fallback="path/to/experiment_config_1.yaml"
)
```

You then need to specify the experiment config to use when calling your code.
The `fallback` argument is optional and specifies which config to use if none
is specified by the command line. To specify the experiment config path in the
command line, simply use the following syntax :

```commandline
python m.py --config path/to/experiment_config_1.yaml
```

You can specify a list of configs to be merged is that order using either of
those two syntaxes :

```commandline
python m.py --config [path/to/experiment_config_1.yaml,path/to/experiment_config_2.yaml]
python m.py --config path/to/experiment_config_1.yaml,path/to/experiment_config_2.yaml
```

#### Changing parameters from the command line

When configuring an experiment, it is often very practical to just change one
or two parameters from the command line to avoid modifying any file or creating
new ones. The configuration system is completely intended to be used that way,
and thus supports merging new parameter values from the command line. To merge
the content of the command line into a config, one needs to call the
merge_from_command_line method :

```python
config = ProjectConfiguration.load_config("path/to/experiment_config_1.yaml")
config.merge_from_command_line()
```

This will look in the command line for any pattern of the type
`--param_name=new_value`, in other words a part of the command surrounded by
spaces (or finished with the end of the line), started by `--`, then having
the name of an existing parameter (also supports “.” and “*” parameter
matching), then the `=` character and finally the new value written
**with no space** (if you need to write spaces for example in a string, please
write the string between quotes). Here are five examples to show how to
overwrite a boolean, a float, a list, a dictionary or a string with a
white space :

```commandline
python main.py --use_squeeze_excitation=true
python main.py --learning_rate=0.1
python main.py --lr_layer_grid_search=[lr_variations,layers_variations]
python main.py --model_kwargs=\{number_of_layers:5,number_of_filters:16\}
python main.py --experiment_name="My experiment"
```

Our in-house parsing method is not very advanced, so a few rules need to be
respected :

- there should be no space inside the section that sets a parameter (see
examples above)
- the set parameter should always be of the same type than the new parameter.
For instance, a param set to None cannot be changed with the command line
(because only None has type NoneType), a list containing one string and one
float needs to be over-ridden with a new string containing exactly a string
and a float in this order, etc.
- the `*`, `{` and `}` characters need to be escaped

### Changing the overwriting regime

The overwriting regime is an internal parameter of the config system which
defines what can and cannot be done when trying to set a config parameter
outside a merge. For example, what happens as a result of the following code
depends on the overwriting regime :

```python
config = ProjectConfiguration.load_config("path/to/experiment_config_1.yaml")
config.save("save.yaml")

config.learning_rate = 0.2
run_experiment(config)
config.learning_rate = 0.1
run_experiment(config)
```

Here the experimenter tried to perform a first experiment with a learning rate
of `0.2`, then a second one with a learning rate of `0.1`. This is obviously
not the best way of doing things (see “_Advanced features : Defining variations
for a config_“), but the config system still supports it to remain flexible if
a user would for some reason have to do this. There are three possible values
for the `overwriting_regime` internal parameter :

- `overwriting_regime = "locked"` : a config cannot be changed in such a way.
The code above would throw an error at lines 4 and 6.

- `overwriting_regime = "unsafe"` : no checks are performed and the changes
are made according to the code. The code above would work as intended but the
saved config would not necessarily be able to reproduce the results if lines 4
and 6 are removed when the experiment is done. The saved config would also not
give an accurate understanding of what happened during the experiment.

- `overwriting_regime = "auto-save"` : (**default value**) when the user tries
to change the config, if the config was saved before, the save is automatically
over-written with the new value to keep it consistent with the values used in
the code. This is obviously not completely fool-proof, and especially fails in
the use case above. On line 4, the save is over-written and then the experiment
is run. But then the save is over-written again on line 6 and the experiment is
run again. Of course, here, the method was doomed to fail from the start since
one saved config cannot hold information about two experiments without using
the variations feature. But this is at least better than before because if
the logs of the second experiments also over-wrote the logs of the first
experiment, then at least the saved logs are consistent with the saved config.

The config system will log warnings to stdout whenever a save is over-written,
and will also warn the user about potential reproducibility issues when loading
a save produced with an `"unsafe"` config.

The overwriting_regime can be set in any function that creates a config,
namely `Configuration.__init__`, `Configuration.load_config`,
`Configuration.build_from_argv` and `Configuration.build_from_configs`.

## III) Good practices and advice

WIP
