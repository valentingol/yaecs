# YAECS (Yet Another Experiment Config System) : documentation

---

This documentation page describes our take on config systems : YAECS. It is mainly comprised of the Configuration
object, which is meant to make some operations more practical, including :

- printing, saving and loading configurations easily and in a flexible way
- flexibility to adapt to the size of a project (simple configs for small
projects, multi-file and/or nested configs for large projects)
- making it easy to change the config between two experiments, to implement hyper-parameter searches, or to visualise
the differences between past experiments
- increasing the overall readability of the config files and introducing safeguards against bad practices for projects
with several contributors/use cases
- allowing for every single parameter in a project to be grouped in a single place (the default config) for easy access,
without making the config hard to manipulate and use due to its size

## 0) Our philosophy

Before heading right into the nitty gritty of things, we'd like to take a moment to tell you our thoughts about
experiments and the research process. This will let us define the terms we use throughout this documentation, and if you
realise that we think alike, maybe this config system is for you ;)

### What we call experiments

A research project has many phases. Some are very wild and exploratory, using notebooks or third-party tools to quickly
iterate and visualise. Some others involve debugging or refactoring. What we call **experiments** are the following
situations :

- you run a part of your code to gain **trustworthy knowledge** about a certain component or process in your project.
*This includes for example evaluating a metric to report it in a paper or take an impactful decision for the future of*
*your paper* (rule of importance)
- you run a part of your code **for a long time**, or using a **large amount of data**, or needing **significant**
**computational resources**. *This includes for example training a neural network, evaluating on more than 10 samples,*
*or having to package your code to run it on another machine* (rule of cost)
- the effect you are studying is **complex**, involves **significant portions of code**, or involves interactions
between **several different modules** with distinct purposes that you investigate at the same time. *This includes*
*evaluating a specific function in the context of your entire pipeline, exploring possibilities for more than a day,*
*or changing the behaviour of several components simultaneously* (rule of complexity)

**In those cases, we argue that your action should be regarded as an experiment, and performed under a number of**
**safeguards.** This is the core of our philosophy, and the purpose which this library intends to serve.

### Properties of the ideal experiment

Now that we have outlined the scope of what we consider "experiments", here we describe how we think a good experiment
should be.

- **clear** : understanding your experiment, its purpose, setup and results, should be as simple as possible, be it for
coworkers, the scientific community, or most of the time future you :)
- **reproducible** : running your experiment again, to witness the same behaviour or continue investigating from that
previous state, should be reliable and effortless
- **responsible** : an experiment is an investment of precious resources and a step towards a result with an impact on
our world. For efficiency and accountability, its outcome and context should be logged
- **simple** : we are all human, and projects can be long and taxing. Starting a new experiment should be simple,
enjoyable and exciting

### What we call configs

A very abstract way of viewing experiments is to consider them "processes that use resources to produce outcomes". In
our case, resources are as diverse as the code, the hardware, the data... but for the purpose of this explanation, we
can simplify them in 2 categories : the support and the configuration (config). The support is comprised of all the
resources needed to reproduce all the experiments in your project. All the hardware. All versions of your code and data.
And the config is simply how to configure your support to reproduce a given experiment. Each experiment has its own
config, and the project has a single support which suffices to reproduce any experiment.

In this library, we tackle the config side of things. Other tools such as git, remote deployment to specific hardware or
dataset version control can help setting up and maintaining the support throughout the project.

So then, back to the config. The config generally assumes a certain knowledge of the support, which makes sense in that
it is a configuration *of that support*. Therefore, appropriate naming and organisation should make it obvious, with
that knowledge, which element of the support each part of the config controls. The config is an object which contains
key-value pairs as would a dictionary. When running an experiment, instead of resorting to hard-coded values which
present many issues, the support queries the corresponding config for its values using the keys. Such key-value pairs
are commonly referred to as "parameters" (though from a Machine Learning perspective they are ususally called
hyper-parameters to disambiguate them from learnable parameters).

### How proper configs save the day

The support is usually huge, changes often and is worked on by several people at the same time. For that reason,
reaching our goal of having simple, reproductible, clear experiments can be a daunting task. But is it really ? Thinking
about it, what *distinguishes* experiments, the config, is on the contrary quite simple. Experiments that make too many
factors vary at once are usually a bad practice which users will try to avoid, which means most of the time only a few
differences separate two experiments.

This means at least in principle that setting up your configs, logging them, reading them and sharing them with other
people familiar with the support should be simple, and what is simple is usually also clear and enjoyable. A quick
glance should be sufficient to remind you what this specific experiment was about, and then you can go on to checking
the results. To reproduce an experiment, you simply use the same config, and you can then modify it as you wish.

Of course, not everything is that simple. Complex projects can require hundreds or even thousands of config parameters
to support all existing and potential future experiments. Moreover, two experiments close in time are easy to compare,
but months later, the config may look very different. This is where YAECS comes in.

### The guiding principles of YAECS

YAECS learns from other existing config systems such as YACS or hydra to make it so that :

- integrating the YAECS config system in small projects takes almost no effort at all ;
- the amount of overhead in your main code is minimal ;
- it seemlessly grows and adapts as your project does, accepting an ever-increasing number of parameters and features
while maintaining a similar ease of use ;
- it provides all the flexibility needed to hide away complex parameter processing behind simple APIs. Features that
could be useful to handle configs should be available, and once the relevant feature has been set up in your project,
the ease of use for following experiments should remain unchanged or be improved ;
- it simplifies backward and forward reproducibility and, coupled with a certain rigor when implementing new features,
allows you to reproduce experiments without even checking out another code version. That way, previous experiments can
be reproduced while still benefitting from new codebase improvements ;
- it provides integration with common trackers to log and visualise its configs and the resulting outcome ;
- and it prints warnings or raises errors as a safeguard against bad practices... because we all have those days don't
we ;)

Did we meet all our goals ? Well... that is for you to judge :) if you think we haven't, do leave us issues for us to do
better.
We hope you enjoy your YAECS experience !

## I) Getting started

Getting started with using YAECS requires a single thing : creating a Configuration object containing your parameters.
There are many ways to create this config object, but let us focus on the easiest one.

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

At this point you might think that this is nothing more than a more fancy dictionary... and you'd be right, that's
actually a very good way to think about your config. In fact, because it mostly behaves like a dictionary, it is much
easier to integrate into existing code or libraries which expect dictionaries.

Of course, in many situations, it is much more than a simple dictionary, as we will demonstrate thoughout this
documentation. In this first introduction, we will cover two more things : loading a config from a **yaml file**, and
some basic **command line interaction**. If you want more, we encourage you to keep reading our other tutorials in [the Intermediate section](#intermediate-features-for-more-scalability),
which we give **practical tips** and **best practices** for the management of your config over the course of a project.

The main purpose of using a config system is to manage your parameters more easily by **getting them out of your code**.
So let's do just that :)

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

One way the YAECS config system provides to manage parameters is to edit them from the command line, which is performed
automatically when you create your config. See for yourself :

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

The YAECS command line parser, one of YAECS' many ways of **preparing your experiment's config**, is very flexible and
fast when you want to change only a handful of parameters.

This is as far as we go for this short introduction. If you're already used to config systems and managing config files,
this might be enough to get you started. However, if you've always just used hardcoded values in your code, and maybe
argparse, you might not really know where to start. We advise you to look at [our tutorial in the Intermediate section](#intermediate-features-for-more-scalability), which will walk you
through config management using YAECS from early set-up to advanced usage.

Happy experimenting !

## II) Tutorial to a clean config management

### Basic setup for small projects

You have never used a config system, and you just found out about YAECS ? You've come to the right place ! In this first
part of our tutorial, we will walk you through the basics of setting up your project for easy and safe experiments.

In this first "basic" part of our tutorial, we will :

1) set up the default config for your project
2) explain how to load the config in your code and conduct experiments
3) see our first management tool : sub-configs
4) explain how to access parameters and perform basic actions

Let's start !

#### 1) Creating the default config

To use YAECS in a project, the very first thing to always do is to prepare the default config. The default config needs
to be a YAML file, which will contain **all the parameters for your project** and their default values. We have decided
to enforce the requirement that every single param be in the defaults, because it is both safer and desirable for you.

It is **safer** because if you want to change a parameter and miss-spell its name, YAECS will know that the parameter
name is wrong because it is not in the default config. Therefore instead of starting your experiment with incorrect
values, YAECS will throw an error.

It is **desirable** because it gives you a centralised place where you can look up all the values, all the
hyper-parameters, all the magic numbers, without going through dozens of source files. YAECS is designed so that having
a very large default config never becomes a burden for clarity. Therefore, no need to shy away from having **a lot** of
parameters in there.

YAML is a very intuitive config format. We chose it for its elegance, flexibility and the fact that it supports
comments. If you need, you can find the YAML documentation here :
[https://yaml.org/spec/1.2.2/](https://yaml.org/spec/1.2.2/). Here is the config example we choose to use in this
tutorial :

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

Let us save this under `configs/default.yaml`. We created this config file to give you an example of what it could look
like (and also to show you some nice features later), but yours will most likely be bigger. Here is what we advise you
to store in this default config :

- variables you think you might change later (for example up there `do_test`, `experiment_path`, `train.epochs`, ...)
- variables you don't necessarily want to change, but for which you might want to be able to find the value easily
(for example `use_gpu` or `model.activation`)
- generally any hardcoded value in your code that has an understandable meaning and can be named easily

So yeah... that's gonna be a lot of parameters. Much more than in our simple example here. But fear not, don't be shy,
put them all in. This is by far the most time-consuming part of the process, but you will not regret the time you invest
here. Even if you decide later that YAECS is not for you after all, you can re-use your default config with any other 
tool you decide to go for (if you can't, don't go for it, it's a bad tool).

As for the values to use for the parameters you put in there, well, it's a default config, so use default values. Values
which make sense in general, which will be used "by default" if the user does not specify their own. As you can see with
`experiment_path`, sometimes no value really makes sense for a parameter, for example when this parameter should always
be set by the user in all experiments. In those cases you can use `null`, which is YAML's equivalent for python's
`None`.

And here you go, that's your first (and longest) step out of the way.

#### 2) Loading your config and starting an experiment

Imagine you want to start a new experiment, for example an overfitting experiment. Let us prepare a config file for this
experiment, which we will store in `configs/overfit.yaml`.

```yaml
---  # Experiment config - configs/overfit.yaml

experiment_path: "logs/overfit"
data:
   number_of_samples: 2
   flip_probability: 0
train.batch_size: 2
```

In the example above, many of the characteristics of an "experiment config" can already be seen.
In contrast to the default config :

- it is short and contains only the values that are modified ;
- it cannot add new parameter, only update existing ones.
In this config file, what is being done in this specific experiment is clear at a glance, regardless of the complexity
of the default config. For now, your project's folder should look something like this :

```markdown
project_root
├── configs
│   ├── default.yaml
│   └── overfit.yaml
├── main.py
└── ...
```

And now, let's get down to business and see what the code part of things will look like. Before using YAECS, your
`main.py` might have looked like this :

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
    config = make_config("configs/default.yaml", "configs/overfit.yaml")
    main(config)
```

And there you go ! You have a working example !

Important note : here we use make_config to simplify things, but it will not allow us to leverage all of YAECS'
features.
In the "intermediate" section of this guide, we will learn how to create configs with other, more powerful constructors.

#### 3) An omnipresent feature for config organisation : sub-configs

At this point, we should explain the important aspect of a "sub-config". As you can see from our example above, there 
are parameters in our config that contain other parameters (for example `model`, or `data`). They are defined as YAML
dictionaries, but don't be fooled : they will not be parsed as python `dict` by YAECS, but as sub-configs. It *is*
possible to declare a parameter in the YAML file that will take as value a python `dict`, but to do that, you need to 
*tag* it.

A YAML tag, in YAML, is a small statement starting with a `!` used to "tag" the following value. In YAECS, we use those 
tags to differentiate sub-configs from simple dictionaries. Indeed, in YAML, declaring `dict: a: 1` or its equivalent 
`dict: {a: 1}` will result in YAECS creating a sub-config called `dict`, which contains a param called `a` with value 1.
To instead define a param called `dict` containing a python dict `{"a": 1}`, you need to *tag* this dictionary using a
type-hint : `dict: !type:dict {a: 1}`. You can learn more about type hints in the [corresponding section on type-hinting](#type-hinting-parameters).

Dictionaries **are not** sub-configs. Sub-configs can check and process their parameters, and they can be accessed using
the `config.subconfig.parameter` syntax. They are also restricted to only the parameters which have been defined in the
defaut config. In an experiment config, you can access and modify a single parameter of a subconfig, and the others will
take their default values. When you replace the value of a dict in the experiment config, on the contrary, you have to
write the complete dict, because dict keys have no default values.

Knowing when you want a sub-config and when you want a dict can be tricky and requires experience, but 99% of the time
you can't go much wrong by simply using sub-configs, which is why this was chosen as the default behaviour.

Sub-configs allow you to organise your parameters into categories and sub-categories, which will come in handy in
basically all your projects.

There are **3 ways** to declare parameters in sub-configs in your YAML files. All three of them will work both in
default or experiment configs, and they have the same behaviour. We demonstrate all three of them below :

Using the dot convention (optimal when there is one or two parameters in the sub-config) :

```yaml
---  # Experiment config with dot convention only

experiment_path: "logs/overfit"
data.number_of_samples: 2
data.flip_probability: 0
train.batch_size: 2
```

Using **untagged** dictionnaries (optimal when there are two parameters or more) :

```yaml
---  # Experiment config with tagged dictionnaries only

experiment_path: "logs/overfit"
data:
   number_of_samples: 2
   flip_probability: 0
train:
   batch_size: 2
```

Using **tagged** documents (optimal when the sub-config is complex and/or contains other sub-configs) :

```yaml
---  # Start of a first document, without any tag, therefore within the main config's scope

experiment_path: "logs/overfit"


--- !data  # here we use YAML's syntax to declare a new document. Everything declared in that document will be placed within the scope of the data sub-config
number_of_samples: 2
flip_probability: 0

--- !train  # end of the data document's scope, start of a new document tagged as train
batch_size: 2
```

Notice how, in this last case, you do need to tag the document to indicate the name of the created sub-configs. This tag
will create a sub-config and place all parameters in the document in this sub-config. You can see this as some sort of
scope. 

Those 3 options will result in the exact same behaviour ! Combining them will allow you to adapt your config to complex
situations while keeping things clean.

Now that we have seen how to declare configs and sub-configs, and how to load them into the code, let's wrap up this
first part of our beginner tutorial with the printing, saving and reproducing of configs.

#### 4) Using, printing, saving, reproducing

To wrap up this first part of our tutorial, let's go over four basic operations that you will need over the course of
your experiments : accessing your parameters, printing your config details, saving your config and using it to reproduce
an experiment.

##### Accessing params

Accessing parameters can be done either using standard object operations (such as `config.param` or
`getattr(config, "param"`) or dictionnary operations (such as `config["param"]` or `config.get("param")`). Actually,
many dict methods are implemented for configs, such as `items`, `keys` or `values`. Nevertheless, `Configuration` does
not inherit from `dict`, therefore we also provide the `get_dict` method in case you need your config to be a dict (for
example to pass it to a third-party library which explicitly checks for a `dict` object).

##### Printing configs

You can use `config.details()` to generate a string that describes your config. If you use `print(config.details())`
with our previous config, here is what you get :

```
MAIN CONFIG :
Configuration hierarchy :
> {'learning_rate': 0.001, 'use_bias': True, 'data': {'path': '/path/to/data', 'batch_size': 32}}
 - learning_rate : 0.001
 - use_bias : True
 - data : {'path': '/path/to/data', 'batch_size': 32}
```

Let's discuss in more details the first thing displayed : the config hierarchy. It is a list of paths and dicts which
indicates the order in which different sources were used to create this config. The first one in the list is always the
default config. It is also the only one in the list which is allowed to add new parameters. All the other sources in the
list can only modify parameters which have been set by the default config. This list is quite practical to get a
condensed gist of the idea behind your experiment. For example, if you read :

```bash
- configs/default.yaml
- configs/overfit.yaml
- {data.flip_probability: 0.5}
```

... you might already be able to figure out most parameters, and also the intent behind the experiment, before having
seen any of the parameters at all ! Here the experimenter simply wanted to do an overfitting experiment, and they
activated the flip augmentation (perhaps using the command line interface) to see if this would affect the model's
capability to overfit.

##### Saving configs

Saving a config is as simple as calling `config.save("save_path.yaml")`. This will save two files : `path.yaml` which
contains the full list of all parameters as well as some metadata, and `save_path_hierarchy.yaml` which contains the
config hierarchy we talked about before. The latter is saved in a separate file for easy access because of how practical
it is.

##### Reproducing experiments

Finally, to reproduce an experiment, all you have to do is load the config you saved when running it :

```python
reproduced_config = make_config("configs/default.yaml", "save_path.yaml")
```

The saved config will be used as an experiment config and overwrite the values of the default config with the values of
the experiment to reproduce.

The most certain way to achieve perfect reproducility regardless of the coding practices of the experimenter is to go
back to the git commit where the experiment was performed and use the saved config file. However, by design YAECS makes
it simpler to achieve perfect reproductibility *without* leaving your current branch. This requires additional rigor to
be observed by the experimenter, which we summarise as a set of good practices which you can find in [our workflow section](#4-our-proposed-workflow-to-use-yaecs-efficiently).

This ends the first part of our tutorial, which aimed at teaching you the basics required to integrate YAECS in a small
project and introduce you to its most fundamental features. As of now though, little distinguishes it from its
alternatives like Hydra or YACS. If you want to know more, follow us into [the Intermediate section](#intermediate-features-for-more-scalability).

### Intermediate features for more scalability

Now that you understand the basics of setting up config files for your projects and loading them, let us see how you can
make your life easier with a few more very practical features.

In this second "intermediate" part of this tutorial, we will :

1) go over different ways to create configs
2) explain how to use our command line interface
3) introduce one of our most interesting features : parameter processing
4) suggest a workflow to experiment while taking advantage of YAECS' features
5) explain how to split your config across multiple files
Let us get started.

#### 1) Sub-classing Configuration and using constructors

For now, we have only created configs by passing a dict or a path to our convenient `make_config` utility function. But
in most projects, this won't be the most flexible way to proceed. In any project that you intend to be working on for a
while, we suggest you create your own subclass for the Configuration class. This is slightly more cumbersome, but also
much more scalable and will keep your `main.py` cleaner. Let's create a new file, for example called `config.py`.

```markdown
project_root
├── configs
│   ├── default.yaml
│   └── overfit.yaml
├── main.py
├── config.py
└── ...
```

This file should be seen as a part of your codebase and commited to the project's repository. To re-use the vocabulary
introduced in [the Philosophy section](#0-our-philosophy), it is part of the support. In this file, let's create a basic sub-class.

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

Because the default config can also be seen as a part of the support (because there is one and only one default config
per project and it should be the same for all users), it is required to hard-code it in the subclass definition. There
should **never** be a use case for using a different default config than this one. Contact me if you see one.

The `parameters_pre_processing` and `parameters_post_processing` methods are not required, but they'll come in handy,
though we'll leave them empty for now. You will learn more about them in [the section on parameter processing](#3-parameter-processing-is-awesome).

Now that our subclass is ready, let's come back to our `main.py` and present its 3 constructors, starting with the
simplest : `load_config`.

```python
# import some stuff
from configs.project_config import ProjectSpecificConfiguration

def main(config):
    # runs the project's code
    ...

if __name__ == "__main__":
    # load the config
    config = ProjectSpecificConfiguration.load_config("configs/overfit.yaml")
    main(config)
```

This constructor takes as argument one or several paths or dictionaries, and merges them one after the other into the
default config. Then, it merges [the command line arguments](#2-using-the-command-line-interface), and finally, it performs [post-processing operations](#3-parameter-processing-is-awesome).
The default config path does not need to be specified because it is hardcoded into the subclass.

The fact that the default config path is not clearly written in the `main.py` can be seen as unclear. In particular, if
a user unfamiliar with YAECS reviews the project, they might not expect the default values to be initialised based on a
path hardcoded in a different file. To avoid this issue, you can choose to still pass the default config explicitly
using the `default_config_path` keyword argument, or you can use the `build_from_configs` constructor.

`build_from_configs` also expects one or several config paths or dictionaries as argument, but contrary to `load_config`
it will not use the hard-coded default config, instead using the first provided path or dictionary as the default
config. Otherwise, it behaves like `load_config`. Under the hood, this is what `make_config` uses : it generates a
template sub-class and calls its `build_from_configs` constructor with its arguments. This is why `make_config` will
also implicitly merge [command line parameters](#2-using-the-command-line-interface) and perform [post-processing](#3-parameter-processing-is-awesome).

Finally, a most useful constructor is the `build_from_argv`. Its base usage is to call it without argument :
`MyProjectConfig.build_from_argv()`. As its name implies, it expects to receive the config to merge from the command
line interface. When using this constructor, the command will be parsed for a pattern of the form
`--config path/to/config.yaml`, and the provided path will be used as experiment config. You can also provide several
paths separated by comas : `--config path1,path2`.

By default, `build_from_argv` will raise an error if no such pattern is detected. This is a safety measure against
oversights. However, you can also configure a fallback to be used everytime the `config` flag is not set :
`MyProjectConfig.build_from_argv(fallback="path/to/fallback/config.yaml")`.

`build_from_argv` also accepts config paths or dictionaries as positional arguments. Those configs are merged into the
default config first, followed by the one given in the command line, followed by [the command line params](#2-using-the-command-line-interface). Those
features make it the most convenient and flexible constructor to use in general, thus we will henceforth consider that
your `main.py` looks like this :

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

In this section, you will learn to control your config from the command line interface (CLI). There are two aspects to
this : modifying parameters from the CLI, and choosing your experiment config file from the CLI. We saw how to do the
latter in the previous section already with [the `build_from_argv` constructor](#1-sub-classing-configuration-and-using-constructors), so here we focus on the former.

Let's assume you usually start your python code using something like :

```bash
python main.py
```

If your config is a YAECS config, then any parameter you pass as an argument to your script will be merged at the end of
the config creation, if it corresponds to a parameter. Continuing with the example from the previous tutorial section,
here's what you would do to start a new experiment, still with our overfit experiment config but this time with some
flip probability.

```bash
python main.py --experiment_path logs/overfit_with_flip --data.flip_probability 0.5
```

Here we of course change the name of the experiment, and then also our flip probability. The YAECS parser is quite
flexible, and supports expressions such as `--name value`, `--name=value`, the "\*" wildcard in a param name to match
several params at once (although in shells it needs to be escaped) and of course the dot-convention to access params of
sub-configs.

You might wonder how YAECS knows the type of a value passed as a string through the command line. For example, if you
pass something like `--data.flip_probability 0.5`, how does YAECS know that the value should be a float and not a 
string ? Well, YAECS doesn't know. It simply uses the same parser as YAML. Therefore, as in YAML, if you want to replace
data.flip_probability with a string, you need to write it in quotations : `--data.flip_probability \"0.5\"`. Don't
forget, those quotation marks need to be escaped in shells, otherwise python will never see them ;).

*Note :* if you want to replace a param with the boolean value `True`, you don't need to write it explicitly. If you
don't provide a new value, the CLI parser will assume you want to set the parameter to `True`. For example, to perform
the test in our earlier example :

```bash
python main.py --do_test
```

#### 3) Parameter processing is awesome

Here we present what we believe to be one of YAECS' main improvements over its competitors : parameters processing. The
idea is quite simple : most of the time, it is really useful to be able to perform some kind of processing on your
parameters before using them, and it only makes sense that these operations should be performed by the config system.
Here is why. The config should be prepared such that the code can access it in a simple, reliable and well-organised
manner. But at the same time, the config should be prepared by a human in a clear interface using the YAML language. In
many cases, those two conditions do not fully align, and therefore it makes sense that the config system should be
tasked with translating the config as seen by the human operator into the config as used by the code.

Here are a few example use cases :

- if you want to check the value of a param for safety (see `check` in example below)
- if you want to convert a param to another format (degrees to radians, human-readable to machine-readable etc.)
(see `convert`)
- if you want to use the info in your YAML-supported values to create custom objects (see `instanciate`)
- if you want to control how the config is created via parameters in the config itself (see [splitting configs across multiple files](#5-splitting-a-config-across-multiple-files))
- if you want to prepare or initialise stuff based on the content of the config (for example by creating folders for
your logs) (see `register_as_experiment_path`)

All these use cases are covered by either using parameters **pre-processing**, or parameters **post-processing**. In
this part, we won't go in too much details about the difference between those. Instead, we'll simply provide a few
examples, to make things clearer. We perform a [deeper dive into this mecanism in the Advanced section](#1-a-deep-dive-into-processing-and-type-checking).

Processing is very simple : all you have to do is associate the names of your parameters with functions. Those functions
are required to accept exactly one argument (the previous value of the param), and return exactly one value (the
processed value of the param). Then, during the config creation operations, the specified function will be used when the
specified name is encountered. This mapping between name and function is configured using the dictionary returned by the
`parameters_pre_processing` and `parameters_post_processing` methods in your subclass. Here is an example modified
config.py to implement the above-mentioned processing functions :

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

As you can see, processing is a flexible feature that can enable very complex behaviours depending on your needs. Use
the provided library of pre-built processing functions (see the `yaecs.config.config_processing_functions` module), or build your own ! 

#### 4) Our proposed workflow to use YAECS efficiently

As an experimenter, your goal should be to easily start any experiment you want and enrich your code with new innovative
features without losing reproducibility for older experiments. In this section, we propose a workflow that satisfies
these conditions and address some common issues and concerns.

**STEP 1 : Preparing your project.** At the start of your project, you want to populate a basic default config with
parameters you think you might need. After one or two projects, you will probably have a template or strongly
established habits to help you do that. Those parameters include for example learning rates, numbers of epochs, batch
sizes, data processing parameters, a path where to save your experiment results etc.. Sometimes, you might use existing
research code as a basis for your work. In this case, if said codebase does not have a config, you can simply browse the
code and extract all values from it to the config.

**STEP 2 : Starting an experiment.** To start your first experiment, you might have an idea of something you'd like to
try. Often, this might be for example reproducing the results of a paper. To do this, prepare an experiment config file
that reproduces the values you want to use, then use this file as your experiment config (for example by using
`build_from_argv` and calling your code with [the `--config` flag](#2-using-the-command-line-interface)).

**STEP 3 : Improvising from there.** Very often, an idea sparking an experiment doesn't work right from the start. You
might need to tweak the learning rate, or train slightly longer. We find that, instead of creating a new YAML file for
each small change or changing your experiment configs, it is easier and better practice to make those changes from the
CLI (see [section on CLI](#2-using-the-command-line-interface)). So long as your experiment does not deviate from the experiment config file, it makes sense to iteratively
tweak things from the CLI. This encourages experiment config files to actually take the role of configuring not
experiments but *series* of experiments. Therefore : 
- the default config contains the information relative to the project
- the experiment config contains the information relative to the series of experiment
- the CLI contains the information relative to a specific iteration

**STEP 4 : Adding features and parameters.** It is naive to think you can build your code once and then find the best
solution simply by interacting with the config. You will always need to make changes to the code, to solve bugs, add
features and refactor. It is however possible, by being rigorous, to ensure perfect *forward reproducibility*. Forward
reproducibility means that at any point during development, you can still load old saved configs from past experiments
and they will be perfectly reproduced. To achieve this, you should apply the following rules :
- never rename a parameter or change its default value : always change values from experiment configs ;
- when adding a new feature controled by a new parameter, always make sure that the default value disactivates the new
feature. For example, if you want to add a new data augmentation function, the new parameter "use_new_augmentation"
should be False by default ;
- if you change your [post-processing functions](#1-a-deep-dive-into-processing-and-type-checking), make sure that they still have the same behaviour for values used
previously for your parameters.

For a while, following these rules might be simple. For long projects however, maintaining full forward reproducibility
might be challenging. In [the Advanced section](#advanced-tips-for-larger-projects), we provide more advice to scale up to massive
projects.


#### 5) Splitting a config across multiple files

To wrap up with our intermediate features, we would like to present how to split a config across multiple files. This is
useful to organise large configs containing hundreds of parameters, which can make your config file really long.
Usually, we recommend splitting across a config across 4 files :
- a base file that contains the most general parameters (debug mode, is the experiment a training, a test or an
inference, path to the experiment results, cpu/gpu etc.) ;
- a file for data-related parameters (data paths, sample descriptions, processing parameters etc.) ;
- a file for model-related parameters (architecture, layers, normalisation etc.) ;
- a file for run-related parameters (training params such as epochs, optimiser or batch sizes ; validation params ;
inference params).

Generally speaking, to build a config you only give your Configuration object one path. Therefore, how can you let your
config system know where to look for other files for other parameters ? The answer lies in a feature we've already
seen : parameters processing :). Let us assume the 4 following configs :

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

train:
    batch_size: 8
    epochs: 100
    ...
val.batch_size: 32
test.batch_size: 32
infer.batch_size: 1
```

You might have noticed that the base file - ie. the file we will give to the config system - contains paths to the other
files. All we need to do is tell the config system that those are not just any parameter : they are actually paths that
the config system should use to find the rest of the config. To do this, you can simply assign them the
`register_as_additional_config_file` pre-processing function, for example like this :
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
And there you go ! Now all parameters that end with `_config_file` will be recognised as you trying to add the
corresponding paths to the config.

This ends the Intermediate section of our tutorial. By now, you already know most of what you need to work efficiently
with YAECS. To become a real pro, there is only one section left !

### Advanced tips for larger projects

Now that you might feel better acquainted with the core features of YAECS we can give you more details about a couple of
very nice features which can save you a lot of time in certain particular situations.

In this third "advanced" part we will :

1) tell you more about parameters processing, as well as type-checking
2) give examples to easily configure complex elements such as dataset versions or machine-specific configs
3) showcase a very useful complement to your config : tracking integration
4) present config variations, which is useful to run sweeps over values of a parameter for example
5) discuss the overwriting regime for special use cases

Let us get started for this last section.

#### 1) A (deep) dive into processing and type-checking

To start off with the advanced tutorials, we want to complete our introduction to parameters processing (started in [the Intermediate section](#3-parameter-processing-is-awesome)). As we
have seen before, parameters processing is a versatile tool to build an interface between the user-facing config and the
code-facing config. It can influence the way the config is built, convert parameters, check if the user made a mistake,
and is generally an important feature for YAECS' completeness. In this section, we will go over five important
concepts :
- the difference between pre-processing and post-processing ;
- how to assign processing functions from the YAML file using tags ;
- how to type-hint a parameter with YAECS ;
- managing ordering issues ;
- what a 'hook' is and how to use them.

That's a lot of stuff to cover, so let's get started !

##### Pre-processing or post-processing ?

To understand the difference between pre-processing and post-processing,, we need to understand more deeply how YAECS
processes parameters. When you call any constructor that performs merges, such as `load_config` or `build_from_argv`,
the config system will first add all the parameters from the default config, then successively perform all the merge
operations scheduled by your constructor call, finish things up by merging the command line parameters, and finally
perform **post-processing** operations. Well, we already know what post-processing is then : it happens all the way at
the end, and if you create your config using a single constructor call, it is only called once.

What about **pre-processing** then ? Well, pre-processing is applied to parameters anytime their value would enter the
config. If a value tries to go from a YAML file or an input dictionary to the config, it is first pre-processed and the
pre-processed value is put in the config instead. This means that pre-processing will be called for every modified
parameter at every merge operation.

There is another important difference. In YAECS philosophy, pre-processing serves as a safety net for the user and a way
to interact with the building process of the config as it is performed. In contrast, post-processing should be seen as a
way to prepare the parameters and the code to perform the experiment in the smoothest and clearest way possible. For
this reason, pre-processing functions cannot return types that are incompatible with YAML, such as custom objects, but
post-processing functions can. This implies that when you save your config, the saved state is the state **BEFORE** the
post-processing operations, but **AFTER** the pre-processing operations. Similarly, when loading a previously saved
config, pre-processing operations will be skipped (because they were already performed before saving), but
post-processing operations will be performed.

Then, when should you use which ? Here are general guidelines. You should use **pre-processing** when :
- you want to check the value of a parameter and **raise an error** if it is invalid (that way, the user can know which
merge contained the invalid value) ;
- you want to **harmonise the format** of a parameter from several input options to a single format (that way the saved
file will contain a harmonised format) ;
- you want to **influence the building process** of the config, for example to register additional config files (this is
not possible with post-processing since the building process is already over when it triggers) ;
- you absolutely want your change to be **reflected in the saved config**.

Conversely, you should use **post-processing** when :
- you want to use a parameter to **instantiate a custom object** (which cannot be saved with YAML) ;
- you want something to **trigger only once**, or that only cares about the **final value** of the parameter (for
example creating a folder named according to the parmeter) ;
- you need to use or modify the value of **other parameters** to process a given parameter (those other parameters might
not exist yet when the pre-processing is called, or their value might not be final)

##### Assigning processing functions to parameters from the YAML file

Previously, we saw that you can assign processing functions to parameters by modifying some methods in your
Configuration subclass. Although this is the most flexible way to do it, it is not always the most convenient. For
common processing functions which belong to the YAECS library, it is possible to perform the assignment directly from
the YAML file. This is done using YAML tags. Tags are a YAML feature that allows you to assign a type to a value using
this syntax : `key: !tag value`.

**Important restriction**: YAML tags (except `!dict`) can **only be used in default configs**. This is because tags are
used to register processing functions, which define the structure and behavior of parameters. Experiment configs cannot
add new processing or change the type semantics of parameters. The one exception is the `!dict` tag, which you must use
in experiment configs when you want to override a parameter with a dictionary value (to distinguish it from a
sub-config).

For example, we saw earlier (in [the section on splitting configs](#5-splitting-a-config-across-multiple-files)) that it is possible to make a parameter read another file to add it to the config
using the `register_as_additional_config_file` preprocessing function. Back then, we added the pair
`"*_config_file": self.register_as_additional_config_file` to our `parameters_pre_processing` dict. It would also have
been possible to assign this function directly from the YAML file, using the `!additional_config_file` tag, like
below :

```yaml
---  # Base file (configs/default/base.yaml)

experiment_path: "logs/overfit"
...
data_config_file: !additional_config_file data.yaml
model_config_file: !additional_config_file model.yaml
run_config_file: !additional_config_file run.yaml
```

You can also similarly register your own processing functions using tags. To do this, simply add your processing
function as a method of your Configuration subclass, and decorate it with
`@yaecs.assign_yaml_tag(<"tag">, <"pre"/"post">, <"type-hint">)`.

##### Type-hinting parameters

Type-hinting is a feature that allows you to specify the type of a parameter. Specifying the type of a parameter will
trigger a special processing **right before the pre-processing**, which will raise an error if the type is incorrect.
Type-hinting parameters is a good practice which serves as documentation in the default config as well as a safety net
against unexpected values being entered by the user. It is also a shortcut to writing tons of type checks yourself in
your processing functions. Type-hinting is done using yaml tags with the standard python syntax. YAECS also supports
alternative syntaxes to simplify complex type hints. Here are a few examples :

```yaml
this_is_a_float: !type:float 0.5
this_is_a_string: !type:str "hello"
this_is_a_list_of_floats: !type:List[float] [0.5, 0.6, 0.7]
this_is_a_list_of_strings_or_floats: !type:List[Union[float,str]] [0.5, "hello", 0.7]
this_is_a_bool_or_none: !type:Optional[bool] null
this_is_a_simplified_syntax_for_list_of_floats: !type:[float] [0.5, 0.6, 0.7]
this_is_a_simplified_syntax_for_int_or_bool: !type:(int,bool) true
this_is_a_simplified_syntax_for_list_of_floats_or_strings: !type:[(float,str)] [0.5, "hello", 0.7]
this_is_a_simplified_syntax_for_string_or_list_of_strings: !type:(str,[str]) "hello"
```

Type-hinting should only be done in the default config.

##### Handling ordering issues

There are times when controling the order in which processing functions are called is important. One trivial example of
this is if there are several processing functions assigned to the same parameter. Another more complex example is when
the processing function X for parameter A depends on the value of parameter B, but this value should only be read after
parameter B was processed by processing function Y. To handle these border cases, YAECS provides a way to assign an
ordering to processing functions.

Before seeing how to assign on order to a processing function, it is important to understand that ordering is not
interpreted in the same way for pre-processing and post-processing functions. Indeed, pre-processing functions are
called whenever a key-value pair is added to the config, while all post-processing functions are called at the end of
the building process. Therefore :
- for pre-processing functions, if several functions are assigned to the same parameter, their order defines in which
order those functions should be performed ;
- for post-processing functions, functions assigned to all parameters are called according to their assigned order.

Here is an example : suppose we are creating a config from the dict `{"a": 1, "b": 2}`. `a` has two pre-processing
functions `pre_a_1` and `pre_a_2` and two post-processing function `post_a_1` and `post_a_2`. `b` has one pre-processing
function `pre_b_1` and one post-processing function `post_b_1`. The order of the functions is as follows :
- pre_a_2 < pre_b_1 < pre_a_1
- post_a_2 < post_b_1 < post_a_1
During config building, `a` will be parsed first and processed to be added to the config. `pre_a_2` will be called
first, then `pre_a_1`, according to the order of all the functions assigned to `a`. Then `b` will be parsed and
processed by function `pre_b_1` to be added to the config. This concludes the merge of the dictionary. After this merge,
assuming there is no command line parameters, the post-processing functions will be called starting with `post_a_2`,
then `post_b_1` and finally `post_a_1`.

Now that we understand how ordering works, let us see how to assign an order to a processing function. All functions are
assumed to have an order of 0 by default. To change this, you can decorate your function with
`@yaecs.assign_order(<order>)` or simply set it by doing `my_function.order = <order>`. You can also assign
it per parameter when defining the `parameters_pre_processing` and `parameters_post_processing` methods in your
Configuration subclass :
    
```python
# inside your Configuration subclass
def parameters_pre_processing(self):
    return {
        "a": (pre_a_1, 2),
        "a ": (pre_a_2, 0),
        "b": (pre_b_1, 1),
    }
def parameters_post_processing(self):
    return {
        "a": (post_a_1, 2),
        "a ": (post_a_2, 0),
        "b": (post_b_1, 1),
    }
```
Note how you can assign several functions to the same parameter by adding a space after the name of the parameter. This
is a bit of a hack, but hey, it works ;).

YAECS also provide an Enum (`yaecs.yaecs_utils.Priority`) to help you assign orders to your functions. It has the
following values : `ALWAYS_FIRST` = -20, `OFTEN_FIRST` = -10, `INDIFFERENT`/`SITUATIONAL` = 0, `OFTEN_LAST` = 10 and
`ALWAYS_LAST` = 20.

##### Hooks

In YAECS, a 'hook' is a parameter that holds a special meaning. The config system or your code might not know which
parameter will be the name of the experiment, but it might expect one of the parameters to be the experiment name. This
is especially practical in the YAECS codebase, which should be project-agnostic but still provide features that adapt to
a given config.

For example, when you assign the `register_as_experiment_path` pre-processing function to a parameter, you are also
registering it to the `experiment_path` hook. Then, if for any reason the config system wants to know where your
experiment will be logged, it can access the list of all parameters that were registered to the "experiment_path" hook
and access their value. You can use the same mechanics to create project templates and processing libraries that will
adapt to each project's config.

You can create your own hook and assign parameters to them by decorating one of its processing functions with the
`@yaecs.hook(<hook_name>)` decorator. Then, calling `config.get_hook(<hook_name>)` will return a list of all
parameter names that were assigned to this hook.

You now know absolutely everything about processing functions ! Everything might not seem clear, as some of those
explanations refer to deep YAECS technical details, but as you stumble upon those use cases in your projects, we are
confident that you will grow more familiar with the details and reasons that justify those design choices.

#### 2) Replacing entire config sections by changing one parameter

YAECS offers several ways to efficiently compose config files or config sections. Put together, they can enable complex
parameter management options that will simplify understanding and using the config, at the cost of a bit of setup and
organisation. In this section, we will present three of those features and how they can be used in practice :
- composing files through merging ;
- composing files through loading additional config files ;
- orchestrating sections through processing functions.

##### Composing files through merging

The most straightforward way to compose configs is using the merge hierarchy. As you've seen in earlier sections, you
can pass multiple configs to `load_config()`:

```python
config = MyProjectConfig.load_config([
    "configs/base_experiment.yaml",
    "configs/dataset_v2.yaml",
    "configs/model_large.yaml"
])
```

Each successive config overwrites parameters from previous ones, letting you layer your configuration decisions. This is
particularly useful for experiment families where you have:
- A base experiment config defining the general setup
- Dataset-specific overrides
- Model architecture variations
- Hardware/machine-specific settings

##### Composing files through loading additional config files

For larger projects, you'll want to split your default config across multiple files. Use the `!additional_config_file`
tag in your default config:

```yaml
--- # configs/default/main.yaml
experiment_path: !experiment_path null

# Load other config sections
data_config: !additional_config_file default/data.yaml
model_config: !additional_config_file default/model.yaml
training_config: !additional_config_file default/training.yaml
```

```yaml
--- !data # configs/default/data.yaml
dataset_path: /path/to/data
batch_size: 32
```

The `!additional_config_file` tag tells YAECS to load and merge the specified file. Combined with document tags like
`!data`, this creates organized sub-configs while keeping files at a manageable size.

##### Orchestrating sections through processing functions

Processing functions can dynamically load different config sections based on parameter values. This is powerful for
managing multiple dataset versions, model architectures, or machine configurations:

```python
# In your ProjectSpecificConfiguration class
def parameters_pre_processing(self):
    def load_dataset_config(dataset_name):
        # Dynamically load the right dataset config
        dataset_configs = {
            "cifar10": "configs/datasets/cifar10.yaml",
            "imagenet": "configs/datasets/imagenet.yaml",
            "custom": "configs/datasets/custom.yaml"
        }
        config_path = dataset_configs.get(dataset_name)
        if config_path:
            self.merge(config_path)
        return dataset_name
    
    def load_machine_config(machine_name):
        # Load machine-specific paths and settings
        if machine_name:
            self.merge(f"configs/machines/{machine_name}.yaml")
        return machine_name
    
    return {
        "dataset_name": load_dataset_config,
        "machine_name": load_machine_config,
    }
```

```yaml
--- # experiment.yaml
dataset_name: "imagenet"  # Automatically loads configs/datasets/imagenet.yaml
machine_name: "cluster_gpu"  # Automatically loads configs/machines/cluster_gpu.yaml
learning_rate: 0.01
```

This pattern keeps experiment configs minimal while automatically pulling in the right supporting configurations. It's
especially useful when:
- You have many dataset variants with different preprocessing pipelines
- Different team members work on different machines with different paths
- You want to swap between model architectures that have very different hyperparameters

**Important**: Processing functions run during config construction, so they can call `self.merge()` to modify the config
being built. This is why they're registered in `parameters_pre_processing()` rather than `parameters_post_processing()`.


#### 3) Tracking integration

One of YAECS' most powerful features is its built-in experiment tracking integration. The `Experiment` class wraps your
main function and automatically logs parameters, metrics, and artifacts to multiple tracking backends simultaneously —
MLFlow, ClearML, Sacred, TensorBoard, or a basic file-based logger.

##### Basic usage

The simplest way to use tracking is to wrap your main function with an `Experiment` object:

```python
from yaecs import Experiment

def train_model(config, tracker):
    # Your training code here
    for epoch in range(config.num_epochs):
        loss = train_epoch(...)
        tracker.log_scalar("train/loss", loss)
        tracker.step()  # Move to next step
    return final_results

config = MyProjectConfig.load_config("configs/experiment.yaml")
experiment = Experiment(config, train_model)
results = experiment.run(run_description="Testing new architecture")
```

The `Experiment` automatically:
- Logs all config parameters to the tracking backend(s)
- Creates unique experiment/run names from your config's experiment path
- Handles variations (see next section) by running each one as a separate tracked run
- Provides a `Tracker` object to your main function for logging metrics and artifacts

##### Configuring trackers

Specify which tracking backends to use via a config parameter with the `!tracker_config` tag in your default config:

```yaml
# In your default config
tracker_config: !dict
  type: ["basic", "mlflow", "tensorboard"]  # Use multiple loggers simultaneously
  # Logger-specific settings can go here
```

Available logger types: `"basic"`, `"clearml"`, `"mlflow"`, `"sacred"`, `"tensorboard"`.

##### Logging with the Tracker

The `Tracker` object passed to your main function provides methods to log various types of data:

```python
def train_model(config, tracker):
    for epoch in range(config.num_epochs):
        # Log scalar metrics
        tracker.log_scalar("metrics/train_loss", loss_value)
        tracker.log_scalar("metrics/accuracy", acc_value)
        
        # Log images
        tracker.log_image("visualizations/predictions", image_array)
        
        # Log artifacts (files)
        tracker.log_artifact("checkpoints/model.pt", checkpoint_path)
        
        # Manage timing
        with tracker.time("data_loading"):
            data = load_batch()
        
        # Move to next step (auto-logs timers by default)
        tracker.step()
```

The tracker handles backend-specific differences automatically, so the same code works across all configured loggers.

**Step management**: The tracker maintains an internal step counter that increments with each call to `tracker.step()`.
All logging methods automatically use this current step value, so you don't need to manually pass a `step` parameter to
`log_scalar()`, `log_image()`, or other logging calls. This keeps your code cleaner and ensures consistent step
tracking across all logged values. If you need to log something at a specific step different from the current one, you
can pass the `step` parameter explicitly to any logging method.

**Sub-loggers for organization**: All logging methods accept a `sub_logger` parameter that helps organize your logs into
logical groups. For most backends (Sacred, MLFlow, ClearML), the sub-logger acts as a prefix/folder in the metric name
(e.g., `sub_logger/metric_name`). For TensorBoard specifically, sub-loggers must be declared in the tracker config and
create separate SummaryWriters in separate folders within your log directory:

```yaml
# In your experiment config
tracker_config: !dict
  type: ["tensorboard"]
  sub_loggers: ["train", "val", "test"]  # TensorBoard-specific: pre-declare sub-loggers
```

```python
tracker.log_scalar("loss", train_loss, sub_logger="train")  # Organized under train/
tracker.log_scalar("loss", val_loss, sub_logger="val")      # Organized under val/
```

This is useful when you want to separate logs for different phases (train/val/test), different models, or any other
logical grouping. Note that TensorBoard requires sub-loggers to be declared in the config, while other backends accept
any sub-logger name on the fly.

##### Parameter filtering

By default, the `Experiment` logs all parameters that differ from the default config. You can customize this:

```python
experiment = Experiment(
    config, main_function,
    log_modified_params_only=False,  # Log all params, not just modified ones
    do_not_log_hooks=True,           # Exclude hook parameters
    params_not_to_log=["internal_*", "debug_mode"],  # Exclude specific patterns
    only_params_to_log=["model.*", "training.*"]      # Only log matching patterns
)
```

For full control, provide a custom filtering function:

```python
def my_filter(config):
    # Return list of parameter names to log
    return [name for name in config.get_parameter_names() if should_log(name)]

experiment = Experiment(config, main_function, params_filter_fn=my_filter)
```

This tracking integration makes YAECS particularly valuable for ML experimentation, as it combines configuration
management with experiment logging in a unified workflow.


#### 4) Variations and Grid Searches

When exploring hyperparameter spaces, you often need to run the same experiment multiple times with different parameter
values. YAECS provides a built-in variations system that lets you define these sweeps directly in your config, keeping
everything organized in a single file rather than managing dozens of separate config files.

##### Basic variations

Define variations as a list of configs to merge into copies of your parent config. Each variation can modify one or
multiple parameters.

First, register the parameter with the `!variations` tag in your default config:

```yaml
--- # default_config.yaml
learning_rate: 0.1
num_layers: 5
batch_size: 32

variations: !variations null
```

Then specify the actual variations in your experiment config using `!dict` to ensure it's treated as a dict rather than
a sub-config:

```yaml
--- # experiment_config.yaml
learning_rate: 0.1
num_layers: 5
batch_size: 32

variations: !dict
  - learning_rate: 0.1
  - learning_rate: 0.01
  - learning_rate: 0.001
    batch_size: 64  # This variation changes both learning_rate and batch_size
```

Then iterate over the variations in your code:

```python
config = MyProjectConfig.load_config("experiment_config.yaml")
config.save("experiment_config.yaml")  # Save parent config once

for variation_config in config.create_variations():
    run_experiment(variation_config)
```

This creates three child configs, each with a different learning rate. Since all variations are defined in the parent
config file, you only need to save that one file to reproduce all experiments.

##### Multiple variation groups

You can define multiple variation groups that operate independently. Instead of using lists, you can use dictionaries to
give each variation a descriptive name.

In your default config, register all variation parameters with the `!variations` tag:

```yaml
--- # default_config.yaml
learning_rate: 0.1
num_layers: 5
num_filters: 64

lr_variations: !variations null
filter_variations: !variations null
```

In your experiment config, specify the variations using `!dict`:

```yaml
--- # experiment_config.yaml
lr_variations: !dict
  high: {learning_rate: 0.1}
  medium: {learning_rate: 0.01}
  low: {learning_rate: 0.001}

filter_variations: !dict
  - num_filters: 32
  - num_filters: 64
  - num_filters: 128
```

When using dictionaries, the keys (`high`, `medium`, `low`) become the variation names visible in your tracking logs.
List-based variations are numbered automatically. This creates 6 children: three named lr variations (with default
filters) and three numbered filter variations (with default learning rate).

##### Grid searches

To create a grid search where variation groups interact combinatorially, register the parameters with `!variations` and
`!grid` tags in your default config:

```yaml
--- # default_config.yaml
learning_rate: 0.1
num_layers: 5

lr_variations: !variations null
layer_variations: !variations null
lr_layer_grid: !grid null
```

Then specify the values in your experiment config:

```yaml
--- # experiment_config.yaml
lr_variations: !dict
  - learning_rate: 0.1
  - learning_rate: 0.01

layer_variations: !dict
  - num_layers: 3
  - num_layers: 5
  - num_layers: 7

lr_layer_grid: !dict [lr_variations, layer_variations]  # Creates 2×3=6 combinations
```

The `lr_layer_grid` parameter lists which variation groups should form a grid. This creates 6 child configs covering all
combinations of the two learning rates and three layer counts.

##### Integration with Experiment tracking

Variations integrate seamlessly with the `Experiment` class. When you call `experiment.run()`, it automatically detects
variations and runs a separate tracked experiment for each one:

```python
experiment = Experiment(config, train_model)
results = experiment.run(run_description="Grid search over lr and layers")
# Automatically creates and tracks one run per variation
```

Each variation gets its own run name and the variation parameters are logged to your tracking backend, making it easy to
compare results across the sweep.

##### Variations in sub-configs

Variations can reference parameters in sub-configs using dot notation.

In your default config:

```yaml
--- # default_config.yaml
model_config_path: path/to/model_config.yaml

filter_variations: !variations null
```

In your experiment config:

```yaml
--- # experiment_config.yaml
filter_variations: !dict
  - model.num_filters: 32
  - model.num_filters: 64

--- !model # model_config.yaml  
num_filters: 32
```

All variation parameters must be defined in the root config file, but they can target parameters anywhere in the config
hierarchy.

This variations system keeps your experiment sweeps organized and reproducible while integrating naturally with YAECS'
merge-based philosophy and tracking capabilities.

#### 5) Overwriting regime : a niche feature for special cases

By design, **YAECS strongly discourages modifying config parameters after creation**. The proper way to change
parameters is through merge operations (`config.merge()`), which maintain a clear hierarchy and ensure reproducibility.
However, for very specific use cases, YAECS provides the **overwriting regime** parameter to control what happens if you
attempt direct parameter assignment (e.g., `config.param = value`) after the config has been created.

By default, YAECS uses the `"locked"` regime, which **prevents such modifications entirely**. This is a deliberate design
choice to enforce good practices :

```python
config = MyProjectConfig.load_config("configs/experiment.yaml")
config.learning_rate = 0.001  # RuntimeError: Overwriting params in locked configs is not allowed
```

This safeguard ensures that your config hierarchy remains clean and that all parameter changes are properly tracked. If
you need to modify a parameter, use `config.merge({"learning_rate": 0.001})` instead.

In rare cases where you absolutely need different behavior, two alternative regimes exist :

- **`"unsafe"`** : Allows direct modification but saved config files are not updated, leading to potential
reproducibility issues. YAECS will warn you when loading configs saved in this mode. Only use this for throwaway
prototyping or debugging.

- **`"auto-save"`** : Allows direct modification and automatically updates the saved config file. While more forgiving
than unsafe mode, this can still lead to confusion if you modify parameters multiple times, as only the final value is
saved.

Both alternatives can be set via the `overwriting_regime` parameter in constructors :

```python
config = MyProjectConfig.load_config("configs/experiment.yaml", overwriting_regime="unsafe")
```

**We strongly recommend** sticking with the default `"locked"` regime and using merge operations for all parameter
changes. This keeps your experiment workflow clear, reproducible, and maintainable.

## III) How-to Recipes

This section provides quick recipes for common tasks you'll encounter when using YAECS in your projects.

### Comparing two configs

To see what differs between two configs (useful for understanding experiment variations):

```python
config1 = MyProjectConfig.load_config("configs/exp1.yaml")
config2 = MyProjectConfig.load_config("configs/exp2.yaml")

differences = config1.compare(config2)
for diff in differences:
    print(f"{diff[0]}: {diff[1]} -> {diff[2]}")
```

### Using config history for reproducibility

Every config tracks its merge history, which you can inspect:

```python
config = MyProjectConfig.load_config("configs/experiment.yaml")
print(config.config_metadata["config_hierarchy"])
# Shows: [path/to/default.yaml, configs/experiment.yaml, {cli_param: value}, ...]
```

When you save a config, two files are created:
- `config.yaml` - full configuration state
- `config_hierarchy.yaml` - the merge sequence used to create it

To reproduce an experiment, just load the saved config:

```python
config = MyProjectConfig.load_config("saved_experiments/exp_001/config.yaml")
```

### Pattern matching with wildcards

Use `*` wildcards in parameter names for bulk operations:

```python
# In pre-processing
def parameters_pre_processing(self):
    return {
        "*_path": Path,  # Convert all params ending in _path to Path objects
        "model.*": validate_model_param,  # Validate all model sub-config params
    }

# In CLI
python main.py --"model.*_size"=128  # Set all size params in model subconfig
```

### Creating configs without YAML files

For scripts and notebooks, use `make_config()` with dictionaries:

```python
from yaecs import make_config

config = make_config({
    "learning_rate": 0.001,
    "batch_size": 32,
    "model": {"layers": 5, "filters": 64}
})
```

### Debugging config issues

Enable verbose logging to see merge operations:

```python
config = MyProjectConfig.load_config("configs/experiment.yaml", verbose=True)
```

Check config state during construction:

```python
# In your ProjectSpecificConfiguration class
def parameters_pre_processing(self):
    def debug_param(value):
        print(f"Processing: {value}")
        print(f"Current config state: {self._state}")
        return value
    
    return {"debug_param": debug_param}
```

### Working with experiment paths

Register a parameter as your experiment path to use it throughout the system:

```yaml
# In default config
experiment_path: !experiment_path null
```

```python
# Access anywhere in your code
exp_path = config.get_experiment_path()

# The Experiment and Tracker classes automatically use this
```

### Using get_template_class for simple projects

For small projects without complex processing needs:

```python
from yaecs import get_template_class

MyConfig = get_template_class(default_config_path="configs/default.yaml")
config = MyConfig.load_config("configs/experiment.yaml")
```

This creates a minimal Configuration subclass without requiring you to define one manually.
