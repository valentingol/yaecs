# YAECS (Yet Another Experiment Config System)

![GitHub last commit (branch)](https://img.shields.io/github/last-commit/valentingol/yaecs/main)
[![License](https://img.shields.io/badge/license-LGPLV3%2B-%23c4c2c2)](https://www.gnu.org/licenses/)

---

This package is a Config System which allows easy manipulation of config files
for safe, clear and repeatable experiments.

[LINK TO DOCUMENTATION](https://github.com/valentingol/yaecs/blob/main/DOCUMENTATION_WIP.md)

## Installation

The package can be installed from our registry using pip: `pip install yaecs`

## Getting started

This package is adapted to a *project* where you need to run a number of
experiments. In this setup, it can be useful to gather all the parameters in
the project to a common location, some "config files", so you can access and
modify them easily. This package is based on YAML, therefore your config files
should be YAML files. One such YAML file could be :

```yaml
gpu: true
data_path: "./data"
learning_rate: 0.01
```

Those will be the default values for those three parameters, so we will keep
them in the file `my_project/configs/default.yaml`. Then, we just need to
read the config in the code using `yaecs.make_config`. That's all there is to 
it: `config = yaecs.make_config("my_project/configs/default.yaml")`, 
we can then call `config.data_path` or `config.learning_rate` to get their 
values as defined in the default config. Now, for example, your main.py could
look like:

```python
from yaecs import make_config

if __name__ == "__main__":
    config = make_config("my_project/configs/default.yaml")
    print(config.details())
```

Then, calling `python main.py --learning_rate=0.001` would parse
the command line and find the pre-existing parameter learning_rate, then change
its value to 0.001.

Many, many more features are available in YAECS ! But even with just this, you 
should be ready to start configuring your experiments. Check out the documentation
for more when you need it !

## Contribution

We welcome contributions to this repository via the
[GitLab repository](https://gitlab.com/reactivereality/public/yaecs).

## License

This repository is licensed under the
[GNU Lesser General Public License](https://www.gnu.org/licenses/lgpl-3.0.en.html).
It is free to use and distribute but modifications are not allowed.
