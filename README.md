# YAECS (Yet Another Experiment Config System)

[![License](https://img.shields.io/badge/license-LGPLV3%2B-%23c4c2c2)](https://www.gnu.org/licenses/)

![GitHub last commit (branch)](https://img.shields.io/github/last-commit/valentingol/yaecs/main)
[![PyPI version](https://badge.fury.io/py/yaecs.svg)](https://badge.fury.io/py/yaecs)

[![Documentation Status](https://readthedocs.org/projects/yaecs/badge/?version=latest)](https://yaecs.readthedocs.io/en/latest/?badge=latest)

---

## Documentation: [here](https://yaecs.readthedocs.io/en/stable/)

This package is a Config System which allows easy manipulation of config files for safe, clear and repeatable
experiments. In a few words, it is:

- built for Machine Learning with its constraints in mind, but also usable out-of-the-box for other kinds of projects ;
- built with scalability in mind and can adapt just as easily to large projects investigating hundreds of well-organised
parameters across many experiments ;
- designed to encourage good coding practices for research purposes, and if used rigorously will ensure a number of
highly desirable properties such that **maintenance-less forward-compatibility** of old configs, **easy
reproducibility** of any experiment, and **extreme clarity** of former experiments for your future self or
collaborators.

[LINK TO DOCUMENTATION](https://github.com/valentingol/yaecs/blob/main/DOCUMENTATION_WIP.md)

## Installation

The package can be installed from pipy:

```bash
pip install yaecs
```

## Getting started

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

Of course, in many situations, it is much more than a simple dictionary, as we demonstrate thoughout our
documentation. In this first introduction, we will cover two more things : loading a config from a **yaml file**, and
some basic **command line interaction**. If you want more, we encourage you to keep reading our other tutorials in
which we give **practical tips** and **best practices** for the management of your config over the course of a project.

The main purpose of using a config system is to manage your parameters more easily by **getting them out of your code**.
So let's do just that :)

We will create a file called `config.yaml` in the root of our project, next to our `main.py` :

```yaml
batch_size: 32
experiment_name: overfit
learning_rate: 0.001
```

Then, in your `main.py`, all you need to do is use the path to the file instead of the dictionary :

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
argparse, you might not really know where to start. We advise you to look at our tutorial (in DOCUMENTATION_WIP.md), which will walk you
through config management using YAECS from early set-up to advanced usage.

Happy experimenting !
