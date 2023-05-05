# YAECS (Yet Another Experiment Config System) : documentation

---

This documentation page describes our take on config systems : YAECS. It is mainly comprised of the Configuration object, which is meant to make some operations more practical, including :

- printing, saving and loading configurations easily and in a flexible way
- flexibility to adapt to the size of a project (simple configs for small
projects, multi-file and/or nested configs for large projects)
- making it easy to change the config between two experiments, to implement hyper-parameter searches, or to visualise the differences between past experiments
- increasing the overall readability of the config files and introducing safeguards against bad practices for projects with several contributors/use cases
- allowing for every single parameter in a project to be grouped in a single place (the default config) for easy access, without making the config hard to manipulate and use due to its size

## 0) Our philosophy

Before heading right into the nitty gritty of things, we'd like to take a moment to tell you our thoughts about experiments and the research process. This will let us define the terms we use throughout this documentation, and if you realise that we think alike, maybe this config system is for you ;)

### What we call experiments

A research project has many phases. Some are very wild and exploratory, using notebooks or third-party tools to quickly iterate and visualise. Some others involve debugging or refactoring. What we call **experiments** are the following situations :

- you run a part of your code to gain **trustworthy knowledge** about a certain component or process in your project. *This includes for example evaluating a metric to report it in a paper or take an impactful decision for the future of your paper* (rule of importance)
- you run a part of your code **for a long time**, or using a **large amount of data**, or needing **significant computational resources**. *This includes for example training a neural network, evaluating on more than 10 samples, or having to package your code to run it on another machine* (rule of cost)
- the effect you are studying is **complex**, involves **significant portions of code**, or involves interactions between **several different modules** with distinct purposes that you investigate at the same time. *This includes evaluating a specific function in the context of your entire pipeline, exploring possibilities for more than a day, or changing the behaviour of several components simultaneously* (rule of complexity)

**In those cases, we argue that your action should be regarded as an experiment, and performed under a number of safeguards.**
This is the core of our philosophy, and the purpose which this library intends to serve.

### Properties of the ideal experiment

Now that we have outlined the scope of what we consider "experiments", here we describe how we think a good experiment should be.

- **clear** : understanding your experiment, its purpose, setup and results, should be as simple as possible, be it for coworkers, the scientific community, or most of the time future you :)
- **reproducible** : running your experiment again, to witness the same behaviour or continue investigating from that previous state, should be reliable and effortless
- **responsible** : an experiment is an investment of precious resources and a step towards a result with an impact on our world. For efficiency and accountability, its outcome and context should be logged
- **simple** : we are all human, and projects can be long and taxing. Starting a new experiment should be simple, enjoyable and exciting

### What we call configs

A very abstract way of viewing experiments is to consider them "processes that use resources to produce outcomes". In our case, resources are as diverse as the code, the hardware, the data... but for the purpose of this explanation, we can simplify them in 2 categories : the support and the configuration (config). The support is comprised of all the resources needed to reproduce all the experiments in your project. All the hardware. All versions of your code and data. And the config is simply how to configure your support to reproduce a given experiment. Each experiment has its own config, and the project has a single support which suffices to reproduce any experiment.

In this library, we tackle the config side of things. Other tools such as git, remote deployment to specific hardware or dataset version control can help setting up and maintaining the support throughout the project.

So then, back to the config. The config generally assumes a certain knowledge of the support, which makes sense in that it is a configuration *of that support*. Therefore, appropriate naming and organisation should make it obvious, with that knowledge, which element of the support each part of the config controls. The config is an object which contains key-value pairs as would a dictionary. When running an experiment, instead of resorting to hard-coded values which present many issues, the support queries the corresponding config for its values using the keys. Such key-value pairs are commonly referred to as "parameters" (though from a Machine Learning perspective they are ususally called hyper-parameters to disambiguate them from learnable parameters).

### How proper configs save the day

The support is usually huge, changes often and is worked on by several people at the same time. For that reason, reaching our goal of having simple, reproductible, clear experiments can be a daunting task. But is it really ? Thinking about it, what *distinguishes* experiments, the config, is on the contrary quite simple. Experiments that make too many factors vary at once are usually a bad practice which users will try to avoid, which means most of the time only a few differences separate two experiments.

This means at least in principle that setting up your configs, logging them, reading them and sharing them with other people familiar with the support should be simple, and what is simple is usually also clear and enjoyable. A quick glance should be sufficient to remind you what this specific experiment was about, and then you can go on to checking the results. To reproduce an experiment, you simply use the same config, and you can then modify it as you wish.

Of course, not everything is that simple. Complex projects can require hundreds or even thousands of config parameters to support all existing and potential future experiments. Moreover, two experiments close in time are easy to compare, but months later, the config may look very different. This is where YAECS comes in.

### The guiding principles of YAECS

YAECS learns from other existing config systems such as YACS or hydra to make it so that :

- integrating the YAECS config system in small projects takes almost no effort at all ;
- the amount of overhead in your main code is minimal ;
- it seemlessly grows and adapts as your project does, accepting an ever-increasing number of parameters and features while maintaining a similar ease of use ;
- it provides all the flexibility needed to hide away complex parameter processing behind simple APIs. Features that could be useful to handle configs should be available, and once the relevant feature has been set up in your project, the ease of use for following experiments should remain unchanged or be improved ;
- it simplifies backward and forward reproducibility and, coupled with a certain rigor when implementing new features, allows you to reproduce experiments without even checking out another code version. That way, previous experiments can be reproduced while still benefitting from new codebase improvements ;
- it provides integration with common trackers to log and visualise its configs and the resulting outcome ;
- and it prints warnings or raises errors as a safeguard against bad practices... because we all have those days don't we ;)

Did we meet all our goals ? Well... that is for you to judge :) if you think we haven't, do leave us gitlab issues for us to do better.
We hope you enjoy your YAECS experience !

## I) Getting started

Getting started with using YAECS requires a single thing : creating a Configuration object containing your parameters. There are many ways to create this config object, but let us focus on the easiest one.

```python
from yaecs import make_config

dictionary = {
    "batch_size": 32,
    "experiment_name": "overfit",
    "learning_rate": 0.001
}
config = make_config(dictionary)
```

And there you go, you have a config. You can query it using usual dictionary or object attribute getters such as :

```python
print(config.batch_size)  # 32
print(config["experiment_name"])  # overfit
print(config.get("learning_rate", None))  # 0.001
```

At this point you might think that this is nothing more than a more fancy dictionary... and you'd be right, that's actually a very good way to think about your config. In fact, because it mostly behaves like a dictionary, it is much easier to integrate into existing code or libraries which expect dictionaries.

Of course, in many situations, it is much more than a simple dictionary, as we will demonstrate thoughout this documentation. In this first introduction, we will cover two more things : loading a config from a **yaml file**, and some basic **command line interaction**. If you want more, we encourage you to keep reading our other tutorials TODO in which we give **practical tips** and **best practices** for the management of your config over the course of a project.

The main purpose of using a config system is to manage your parameters more easily by **getting them out of your code**. So let's do just that :)

We will create a file called `config.yaml` in the root of our project, next to our `main.py` :

```yaml
batch_size: 32
experiment_name: overfit
learning_rate: 0.001
```

Then, in you `main.py`, all you need to do is use the path to the file instead of the dictionary :

```python
from yaecs import make_config

config = make_config("config.yaml")

print(config.batch_size)
print(config["experiment_name"])
print(config.get("learning_rate", None))
```

Now, if you run your script, you should see the same prints as before.

```bash
$ python main.py
[CONFIG] Building config from default : config
32
overfit
0.001
```

One way the YAECS config system provides to manage parameters is to edit them from the command line, which is performed automatically when you create your config. See for yourself :

```bash
$ python main.py --batch_size 16
[CONFIG] Building config from default : config
[CONFIG] Merging from command line : {'batch_size': 16}
16
overfit
0.001
$ python main.py --experiment_name=production --batch_size=16
[CONFIG] Building config from default : config
[CONFIG] Merging from command line : {'experiment_name': 'production', 'batch_size': 16}
16
production
0.001
```

The YAECS command line parser, one of YAECS' many ways of **preparing your experiment's config**, is very flexible and fast when you want to change only a handful of parameters.

This is as far as we go for this short introduction. If you're already used to config systems and managing config files, this might be enough to get you started. However, if you've always just used hardcoded values in your code, and maybe argparse, you might not really know where to start. We advise you to look at our tutorial TODO, which will walk you through config management using YAECS from early set-up to advanced usage.

Happy experimenting !

## II) Tutorial to a clean config management

### Basic setup for small projects

You have never used a config system, and you just found out about YAECS ? You've come to the right place ! In this first part of our tutorial, we will walk you through the basics of setting up your project for easy and safe experiments.

In this first "basic" part of our tutorial, we will :

1) set up the default config for your project
2) explain how to load the config in your code and conduct experiments
3) see our first management tool : sub-configs
4) explain how to access parameters and perform basic actions

Let's start !

#### 1) Creating the default config

To use YAECS in a project, the very first thing to always do is to prepare the default config. The default config needs to be a YAML file, which will contain **all the parameters for your project** and their default values. We have decided to enforce the requirement that every single param be in the defaults, because it is both safer and desirable for you.

It is **safer** because if you want to change a parameter and miss-spell its name, YAECS will know that the parameter name is wrong because it is not in the default config. Therefore instead of starting your experiment with incorrect values, YAECS will throw an error.

It is **desirable** because it gives you a centralised place where you can look up all the values, all the hyper-parameters, all the magic numbers, without going through dozens of source files. YAECS is designed so that having a very large default config never becomes a burden for clarity. Therefore, no need to shy away from having **a lot** of parameters in there.

YAML is a very intuitive config format. We chose it for its elegance, flexibility and the fact that it supports comments (which is not the case in JSON for example). If you need, you can find the YAML documentation here : TODO. Here is the config example we choose to use in this tutorial :

```yaml
---  # Default config - configs/default.yaml

experiment_path: null
use_gpu: true
do_train: true
do_val: true
do_test: false
debug: false

model:
   type: ResNet
   layers: 10
   activations: ReLU

data:
   size: [64, 64]
   number_of_samples: null
   flip_probability: 0.5
   rotate_probability: 0

train:
   epochs: 100
   batch_size: 32
   optimiser:
      type: Adam
      learning_rate: .001
      betas: [0.9, 0.999]
      weight_decay: 0
```

Let us save this under `configs/default.yaml`. We created this config file to give you an example of what it could look like (and also to show you some nice features later), but yours will most likely be bigger. Here is what we advise you to store in this default config :

- variables you intend to change later, or you think you might change later (for example up there `do_test`, `experiment_path`, `train.epochs`, ...)
- variables you don't necessarily want to change, but for which you might want to be able to find the value easily (for example `use_gpu` or `model.activation`)
- generally any hardcoded value in your code that has an understandable meaning

So yeah... that's gonna be a lot of parameters. Much more than in our simple example here. But fear not, don't be shy, put them all in. This is by far the most time-consuming part of the process, but you will not regret the time you invest here. Even if you decide later that YAECS is not for you after all, you will be glad to have it whichever other tool you decide to go for.

As for the values to use for the parameters you put in there, well, it's a default config, so use default values. Values which make sense in general, which will be used "by default" if the user does not specify their own. As you can see with `experiment_path`, sometimes no value really makes sense for a parameter, for example when this parameter should always be set by the user in all experiments. In those cases you can use `null`, which is YAML's equivalent for python's `None`.

And here you go, that's your first (and longest) step out of the way.

#### 2) Loading your config and starting an experiment

Imagine you want to start a new experiment, for example an overfitting experiment. Let us prepare a config file for this experiment, which we will store in `configs/overfit.yaml`.

```yaml
---  # Experiment config - configs/overfit.yaml

experiment_path: "logs/overfit"
data:
   number_of_samples: 2
   flip_probability: 0
train.batch_size: 2
```

In the example above, many if the characteristics of an "experiment config" can already be seen.
In contrast to the default config, it :

- is short and contains only the values that are modified ;
- cannot add new parameter, only update existing ones.
In this config file, what is being done in this specific experiment is clear at a glance, regardless of the complexity of the default config. For now, your project's folder should look something like this :

```markdown
project_root
├── configs
│   ├── default.yaml
│   └── overfit.yaml
├── main.py
└── ...
```

And now, let's get down to business and see what the code part of things will look like. Before using YAECS, your `main.py` might have looked like this :

```python
# import some stuff

def main():
    # runs the project's code
    ...

if __name__ == "__main__":
    # do some setup, for example argparse
    main()
```

And now, how it looks with YAECS :

```python
# import some stuff
from yaecs import make_config

def main(config):
    # runs the project's code
    ...

if __name__ == "__main__":
    # load the config
    config = make_config("configs/overfit.yaml",
                         default_config="configs/default.yaml")
    main(config)
```

Two very important notes here :

- **the code above will not work**, because up to now I ommited an important point to avoid confusion. To see how to fix our current setup, please read the next section about sub-configs ;
- here we use make_config to simplify things, but it will not allow us to leverage all of YAECS' features. In the "intermediate" section of this guide, we will learn how to load configs with other, more powerful functions.

At this point, you probably have many questions... so let's head on to the next sections to answer them !

#### 3) An omnipresent feature for config organisation : sub-configs

The only change we have to do to make everything work is in the configs. I'll first show you the working version, then I'll explain the difference and why it's important.

In the default config :

```yaml
---  # Default config - configs/default.yaml

experiment_path: null
use_gpu: true
do_train: true
do_val: true
do_test: false

model: !model
   type: ResNet
   layers: 10
   activations: ReLU

data: !data
   size: [64, 64]
   number_of_samples: null
   flip_probability: 0.5
   rotate_probability: 0

train: !train
   epochs: 100
   batch_size: 32
   optimiser: !optimiser
      type: Adam
      learning_rate: .001
      betas: [0.9, 0.999]
      weight_decay: 0
```

... and in the experiment config :

```yaml
---  # Experiment config - configs/overfit.yaml

experiment_path: "logs/overfit"
data: !data
   number_of_samples: 2
   flip_probability: 0
train.batch_size: 2
```

What we did is rather simple : for every parameter which contains other parameters (referred to as "sub-configs"), we added a so-called YAML tag. A YAML tag, in YAML, is a small statement starting with a `!` used to "tag" the following value. In YAECS, we use those tags to differentiate sub-configs from simple dictionaries.

Indeed, in YAML, declaring `dict: a: 1` or its equivalent `dict: {a: 1}` defines a python `dict` by default. To define a YAECS sub-config instead, you need to *tag* this dictionary using a tag that is **exactly the parameter's name**, for example `subconfig: !subconfig {a: 1}`.

Dictionaries **are not** sub-configs. Sub-configs can check and process their parameters, and they can be accessed using the `config.subconfig.parameter` syntax. They are also restricted to only the parameters which have been defined in the defaut config. In an experiment config, you can access and modify a single parameter of a subconfig, and the others will take their default values. When you replace the value of a dict in the experiment config, on the contrary, you have to write the complete dict, because dict keys have no default values.

Knowing when you want a sub-config and when you want a dict can be tricky and requires experience, but most of the time you can't go much wrong by simply declaring **all** your dicts as sub-configs instead.

Sub-configs allow you to organise your parameters into categories and sub-categories, which will come in handy in basically all your projects.

In the following, we re-write the previous experiment config using **3 ways** to declare parameters in sub-configs. All three of them will work both in default or experiment configs.

Using the dot convention (optimal when there is one or two parameters in the sub-config) :

```yaml
---  # Experiment config with dot convention only

experiment_path: "logs/overfit"
data.number_of_samples: 2
data.flip_probability: 0
train.batch_size: 2
```

Using tagged dictionnaries (optimal when there are two parameters or more) :

```yaml
---  # Experiment config with tagged dictionnaries only

experiment_path: "logs/overfit"
data: !data
   number_of_samples: 2
   flip_probability: 0
train: !train
   batch_size: 2
```

Using tagged documents (optimal when the sub-config is complex and/or contains other sub-configs) :

```yaml
---  # Start of a first document, without any tag, therefore within the main config's scope

experiment_path: "logs/overfit"


--- !data  # here we use YAML's syntax to declare a new document. Everything declared in that document will be placed within the scope of the data sub-config
number_of_samples: 2
flip_probability: 0

--- !train  # end of the data document's scope, start of a new document tagged as train
batch_size: 2
```

Those 3 options will result in the exact same behaviour ! Combining them will allow you to adapt your config to complex situations while keeping things clean.

Now that we have seen how to declare configs and sub-configs, and how to load them into the code, let's wrap up this first part of our beginner tutorial with the printing, saving and reproducing of configs.

#### 4) Using, printing, saving, reproducing

To wrap up this first part of our tutorial, let's go over four basic operations that you will need over the course of your experiments : accessing your parameters, printing your config details, saving your config and using it to reproduce an experiment.

##### Accessing params

Accessing parameters can be done either using standard object operations (such as `config.param` or `getattr(config, "param"`) or dictionnary operations (such as `config["param"]` or `config.get("param")`). Actually, many dict methods are implemented for configs, such as `items`, `keys` or `values`. Nevertheless, `Configuration` does not inherit from `dict`, therefore we also provide the `get_dict` method in case you need your config to be a dict (for example to pass it to a third-party library which explicitly checks for a `dict` object).

##### Printing configs

You can use `config.details()` to generate a string that describes your config. If you use `print(config.details())` with our previous config, here is what you get : TODO

Let's discuss in more details the first thing displayed : the config hierarchy. It is a list of path and dicts which indicates the order in which different sources were used to create this config. The first one in the list is always the default config. It is also the only one in the list which is allowed to set new parameters. All the other sources in the list can only modify parameters which have been set by the default config. This list is quite practical to get a condensed gist of the idea behind your experiment. For example, if you read :

```bash
- configs/default.yaml
- configs/overfit.yaml
- {data.flip_probability: 0.5}
```

... you might already be able to figure out most parameters, and also the intent behind the experiment, before having seen any of the parameters at all ! Here the experimenter simply wanted to do an overfitting experiment, and they activated the flip augmentation (perhaps using the command line interface) to see if this would affect the model's capability to overfit.

##### Saving configs

Saving a config is as simple as calling `config.save("save_path.yaml")`. This will save two files : `path.yaml` which contains the full list of all parameters as well as some metadata, and `save_path_hierarchy.yaml` which contains the config hierarchy we talked about before. The latter is saved in a separate file for easy access because of how practical it is.

##### Reproducing experiments

Finally, to reproduce an experiment, all you have to do is load the config you saved when running it :

```python
reproduced_config = make_config("save_path.yaml",
                                default_config="configs/default.yaml")
```

The saved config will be used as an experiment config and overwrite the values of the default config with the values of the experiment to reproduce.

The most certain way to achieve perfect reproducility regardless of the coding practices of the experimenter is to go back to the git commit where the experiment was performed and use the saved config file. However, by design YAECS makes it simpler to achieve perfect reproductibility *without* leaving your current branch. This requires additional rigor to be observed by the experimenter, which we summarise as a set of good practices which you can find here TODO.

This ends the first part of our tutorial, which aimed at teaching you the basics required to integrate YAECS in a small project and introduce you to its most fundamental features. As of now though, nothing distinguishes it from its alternatives like Hydra or YACS. If you want to know more, follow us into the second part of our tutorial : TODO

### Intermediate features for more scalability

Now that you understand the basics of setting up config files for your projects and loading them, let us see how you can make your life easier with a few more very practical features.

In this second "intermediate" part of this tutorial, we will :

1) go over different ways to create configs
2) explain how to use our command line interface
3) introduce one of our most interesting features : parameter processing
4) suggest a workflow to experiment while taking advantage of YAECS' features
5) explain how to split your config across multiple files
Let us get started.

#### 1) Sub-classing Configuration and using constructors

For now, we have only created configs by passing a dict or a path to our convenient `make_config` utility function. But in most projects, this won't be the most flexible way to proceed. In any project that you intend to be working on for a while, we suggest you create your own subclass for the Configuration class. This is slightly more cumbersome, but also much more scalable and will keep your `main.py` cleaner. Let's create a new file, for example called `config.py`.

```markdown
project_root
├── configs
│   ├── default.yaml
│   └── overfit.yaml
├── main.py
├── config.py
└── ...
```

This file should be seen as a part of your codebase and commited to the project's repository. To re-use the vocabulary introduced in section 0 (TODO), it is part of the support. In this file, let's create a basic sub-class.

```python
from yaecs import Configuration

class MyProjectConfig(Configuration):
    @staticmethod
    def get_default_config_path():
        return "configs/default.yaml"

    def parameters_pre_processing(self):
        return {}

    def parameters_post_processing(self):
        return {}
```

Because the default config can also be seen as a part of the support (because there is one and only one default config per project and it should be the same for all users), it is required to hard-code it in the subclass definition. There should never be a use case for using a different default config than this one.

The `parameters_pre_processing` and `parameters_post_processing` methods are not required, but they'll come in handy, though we'll leave them empty for now. You will learn more about them in a future section (TODO).

Now that our subclass is ready, let's come back to our `main.py` and present its 3 constructors, starting with the simplest : `load_config`.

```python
# import some stuff
from config import MyProjectConfig

def main(config):
    # runs the project's code
    ...

if __name__ == "__main__":
    # load the config
    config = MyProjectConfig.load_config("configs/overfit.yaml")
    main(config)
```

This constructor takes as argument one or several paths or dictionaries, and merges them one after the other into the default config. Then, it merges the command line arguments (TODO), and finally, it performs post-processing operations (TODO).  The default config path does not need to be specified because it is hardcoded into the subclass.

The fact that the default config path is not clearly written in the `main.py` can be seen as unclear. In particular, if a user unfamiliar with YAECS reviews the project, they might not expect the default values to be initialised based on a path hardcoded in a different file. To avoid this issue, you can choose to still pass the default config explicitly using the `default_config_path` keyword argument, or you can use the `build_from_configs` constructor.

`build_from_configs` also expects one or several config paths or dictionaries as argument, but contrary to `load_config` it will not use the hard-coded default config, instead using the first provided path or dictionary as the default config. Otherwise, it behaves like `load_config`. Under the hood, this is what `make_config` uses : it generates a template sub-class and calls its `build_from_configs` constructor with its arguments. This is why `make_config` will also implicitly merge command line parameters (TODO) and perform post-processing (TODO).

Finally, a most useful constructor is the `build_from_argv`. Its base usage is to call it without argument : `MyProjectConfig.build_from_argv()`. As its name implies, it expects to receive the config to merge from the command line interface. When using this constructor, the command will be parsed for a pattern of the form `--config path/to/config.yaml`, and the provided path will be used as experiment config. You can also provide several paths separated by comas : `--config path1,path2`.

By default, `build_from_argv` will raise an error if no such pattern is detected. This is a safety measure against oversights. However, you can also configure a fallback to be used everytime the `config` flag is not set : `MyProjectConfig.build_from_argv(fallback="path/to/fallback/config.yaml")`.

`build_from_argv` also accepts config paths or dictionaries as positional arguments. Those configs are merged into the default config first, followed by the one given in the command line, followed by the command line params (TODO). Those features make it the most convenient and flexible constructor to use in general, thus we will henceforth consider that your `main.py` looks like this :

```python
# import some stuff
from config import MyProjectConfig

def main(config):
    # runs the project's code
    ...

if __name__ == "__main__":
    # load the config
    config = MyProjectConfig.build_from_argv(fallback="configs/overfit.yaml")
    main(config)
```

#### 2) Using the command line interface

In this section, you will learn to control your config from the command line interface (CLI). There are two aspects to this : modifying parameters from the CLI, and choosing your experiment config file from the CLI. We saw how to do the latter in the previous section already with the `build_from_argv` constructor (TODO), so here we focus on the former.

Let's assume you usually start your python code using something like :

```bash
python main.py
```

If your config is a YAECS config, then any parameter you pass as an argument to your script will be merged at the end of the config creation, if it corresponds to a parameter. Continuing with the example from the previous tutorial section, here's what you would do to start a new experiment, still with our overfit experiment config but this time with some flip probability.

```bash
python main.py --experiment_path logs/overfit_with_flip --data.flip_probability 0.5
```

Here we of course change the name of the experiment, and then also our flip probability. The YAECS parser is quite flexible, and supports expressions such as `--name value`, `--name=value`, the "\*" wildcard in a param name to match several params at once (although in shells it needs to be escaped) and of course the dot-convention to access params of sub-configs.

Most of the time, changing parameters from the CLI is just that simple. It only gets a bit more tricky if you want to change the type of a parameter (ie. replace a param that was a float with a string for instance), or replace entire lists or dicts from the CLI. For those operations, please refer to our dedicated section : TODO.

*Note :* if you want to replace a param with the boolean value `True`, you don't need to write it explicitly. If you don't provide a new value, the CLI parser will assume you want to set the parameter to `True`. For example, to perform the test in our earlier example :

```bash
python main.py --do_test
```

#### 3) Parameter processing is awesome

Here we present what we believe to be one of YAECS' main improvement over its competitors : parameters processing.  The idea is quite simple : most of the time, it is really useful to be able to perform some kind of processing on your parameters before using them, and it only makes sense that these operations should be performed by the config system. Here is why. The config should be prepared such that the code can access it in a simple, reliable and well-organised well. But at the same time, the config should be prepared by a human in a clear interface using the YAML language. In many cases, those two conditions do not fully align, and therefore it makes sense that the config system should be tasked with translating the config as seen by the human operator into the config as used by the code.

Here are a few example use cases :

- if you want to check the value of a param for safety (see `check` in example below)
- if you want to convert a param to another format (degrees to radians, human-readable to machine-readable etc.) (see `convert`)
- if you want to use the info in your YAML-supported values to create custom objects (see `instanciate`)
- if you want to control how the config is created via parameters in the config itself (see next section TODO)
- if you want to prepare or initialise stuff based on the content of the config (for example by creating folders for your logs) (see `register_as_experiment_path`)

All these use cases are covered by either using parameters **pre-processing**, or parameters **post-processing**. In this part, we won't go in too much details about the difference between those. Instead, we'll simply provide a few examples, to make things clearer. We perform a deeper dive into this mecanism here (TODO).

Processing is very simple : all you have to do is associate the names of your parameters with functions. Those functions are required to accept exactly one argument (the previous value of the param), and return exactly one value (the processed value of the param). Then, during the config creation operations, the specified function will be used when the specified name is encountered. This mapping between name and function is configured using the dictionary returned by the `parameters_pre_processing` and `parameters_post_processing` methods in your subclass. Here is an example modified config.py to implement the above-mentioned processing functions :

```python
from pathlib import Path
from yaecs import Configuration

def check(param_to_check):
    if param_to_check < 0:
        raise ValueError("Value should be positive.")
    if param_to_check > 1:
        print("Could be unstable")
    return param_to_check

convert = lambda string: string.strip().lower()

instanciate = lambda path: Path(path)

class MyProjectConfig(Configuration):
    @staticmethod
    def get_default_config_path():
        return "configs/default.yaml"

    def parameters_pre_processing(self):
        return {
            "train.optimiser.learning_rate": check,
            "model.type": convert,
            "model.activations": convert,
        }

    def parameters_post_processing(self):
        return {
            "experiment_path": self.register_as_experiment_path,
            "*_path": instanciate,
        }
```

As you can see, processing is a flexible feature that can enable very complex behaviours depending on your needs. Use the provided library of pre-built processing functions TODO, or build your own ! 

#### 4) Our proposed workflow to use YAECS efficiently

As an experimenter, your goal should be to easily start any experiment you want and enrich your code with new innovative features without losing reproducibility for older experiments. In this section, we propose a workflow that satisfies these conditions and address some common issues and concerns.

**STEP 1 : Preparing your project.** At the start of your project, you want to populate a basic default config with parameters you think you might need. After one or two projects, you will probably have a template or strongly established habits to help you do that. Those parameters include for example learning rates, numbers of epochs, batch sizes, data processing parameters, a path where to save your experiment results etc.. Sometimes, you might use existing research code as a basis for your work. In this case, if said codebase does not have a config, you can simply browse the code and extract all values from it to the config.

**STEP 2 : Starting an experiment.** To start your first experiment, you might have an idea of something you'd like to try. Often, this might be for example reproducing the results of a paper. To do this, prepare an experiment config file that reproduces the values you want to use, then use this file as your experiment config (for example by using build_from_argv and calling your code with the `--config` flag TODO).

**STEP 3 : Improvising from there.** Very often, an idea sparking an experiment doesn't work right from the start. You might need to tweak the learning rate, or train slightly longer. We find that, instead of creating a new YAML file for each small change or changing your experiment configs, it is easier and better practice to make those changes from the CLI TODO. So long as your experiment does not deviate from the experiment config file, it makes sense to iteratively tweak things from the CLI. This encourages experiment config files to actually take the role of configuring not experiments but *series* of experiments. Therefore : 
- the default config contains the information relative to the project
- the experiment config contains the information relative to the series of experiment
- the CLI contains the information relative to a specific iteration

**STEP 4 : Adding features and parameters.** It is naive to think you can build your code once and then find the best solution simply by interacting with the config. You will always need to make changes to the code, to solve bugs, add features and refactor. It is however possible, by being rigorous, to ensure perfect *forward reproducibility*. Forward reproducibility means that at any point during development, you can still load old saved configs from past experiments and they will be perfectly reproduced. To achieve this, you should apply the following rules :
- never rename a parameter or change its default value : always change values from experiment configs ;
- when adding a new feature controled by a new parameter, always make sure that the default value disactivates the new feature. For example, if you want to add a new data augmentation function, the new parameter "use_new_augmentation" should be False by default ;
- if you change your post-processing functions TODO, make sure that they still have the same behaviour for values used previously for your parameters.

For a while, following these rules might be simple. For long projects however, maintaining full forward reproducibility might be challenging. In our advanced tips for larger projects TODO, we provide more advice to scale up to massive projects.


#### 5) Splitting a config across multiple files

To wrap up with our intermediate features, we would like to present how to split a config across multiple files. This is useful to organise large configs containing hundreds of parameters, which can make your config file really long. Usually, we recommend splitting across a config across 4 files :
- a base file that contains the most general parameters (debug mode, is the experiment a training, a test or an inference, path to the experiment results, cpu/gpu etc.) ;
- a file for data-related parameters (data paths, sample descriptions, processing parameters etc.) ;
- a file for model-related parameters (architecture, layers, normalisation etc.) ;
- a file for run-related parameters (training params such as epochs, optimiser or batch sizes ; validation params ; inference parms).

Generally speaking, to build a config you only give your Configuration object one path. Therefore, how can you let your config system know where to look for other files for other parameters ? The answer lie in a feature we've already seen : parameters processing :). Let us assume the 4 following configs :

```
project_root
├── configs
│   ├── default
│   │   ├── base.yaml
│   │   ├── data.yaml
│   │   ├── model.yaml
│   │   └── run.yaml
│   └── overfit.yaml
├── main.py
├── config.py
└── ...
```

```yaml
---  # Base file (configs/default/base.yaml)

experiment_path: "logs/overfit"
...
data_config_file: data.yaml
model_config_file: model.yaml
run_config_file: run.yaml
```

```yaml
--- !data  # Data config file (configs/default/data.yaml)

data_path: ./data
...
processing_pipeline: [Rescale, Noise, Crop, ToTensor]
```

```yaml
--- !model  # Model file (configs/default/model.yaml)

architecture: "mobilenet"
...
normalisation: BatchNorm
```

```yaml
---  # Run file (configs/default/run.yaml)

train: !train
    batch_size: 8
    epochs: 100
    ...
val.batch_size: 32
test.batch_size: 32
infer.batch_size: 1
```

You might have noticed that the base file - ie. the file we will give to the config system - contains paths to the other files. All we need to do is tell the config system that those are not just any parameter : they are actually paths that the config system should use to find the rest of the config. To do this, you can simply assign them the `register_as_additional_config_file` pre-processing function, for example like this :
```python
from yaecs import Configuration

class MyProjectConfig(Configuration):
    @staticmethod
    def get_default_config_path():
        return "configs/default/base.yaml"

    def parameters_pre_processing(self):
        return {
            "*_config_file": self.register_as_additional_config_file,
        }

    def parameters_post_processing(self):
        return {}
```
And there you go ! Now all parameters that end with `_config_file` will be recognised as you trying to add the corresponding paths to the config.

This ends the Intermediate section of our tutorial. By now, you already know most of what you need to work efficiently with YAECS. To become a real pro, there is only one section left !

### Advanced tips for larger projects

Now that you might feel better acquainted with the core features of YAECS we can give you more details about a couple of very nice features which can save you a lot of time in certain particular situations.

In this third "advanced" part we will :

1) tell you more about parameters processing, as well as type-checking
2) give examples to easily configure complex elements such as dataset versions or machine-specific configs
3) present config variations, which is useful to run sweeps over values of a parameter for example
4) showcase our WIP new feature : tracking integration

Let us get started for this last section.

#### 1) A dive into processing and type-checking

WIP

#### 2) Replacing entire config sections by changing one parameter

WIP

#### 3) Variations and Grid Searches

WIP

#### 4) [WIP] Tracking integration

WIP

## How to's

Using configurations in your project includes two main steps : creating the
config files, then loading them in your code. You can then use your configs as you see fit.

Ex :

```markdown
├── src
│   ├── controller
│   │   ├── **/*.css
│   ├── views
│   ├── model
│   ├── index.js
├── public
│   ├── css
│   │   ├── **/*.css
│   ├── images
│   ├── js
│   ├── index.html
├── dist (or build
├── node_modules
├── package.json
├── package-lock.json
└── .gitignore
```

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

#### Loading your config files

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
*“Advanced features : Pre-processing”, “Advanced features : Splitting across
several files” and “Advanced features : Defining variations for a config”*).
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

#### Simple usage examples

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
*“Advanced features : Using the command line support”*.

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
objects (see *“Advanced features : Changing the overwriting regime”*).

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

#### To reproduce experiments

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
next advanced use section : *Defining a config over several files*.

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
nice features of the YAML syntax, the Configuration class allows to organise
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
parameters grows, it would be nice to not only organise those parameters in
different files on the disk, but also organise them in different “sub-configs”
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
not the best way of doing things (see “*Advanced features : Defining variations
for a config*“), but the config system still supports it to remain flexible if
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
