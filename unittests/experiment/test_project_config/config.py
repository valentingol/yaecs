import os
from numbers import Number

from yaecs import Configuration

VALID = ["a", "b", "c", "d"]


def make_list(integer):
    if isinstance(integer, Number):
        return [integer, integer]
    return integer


def e(e):
    if e:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(e)
    return e


class UnifiedSegmentationConfig(Configuration):
    @staticmethod
    def get_default_config_path():
        return os.path.join(os.path.dirname(__file__), "defaults", "default.yaml")
    
    def a_f(self, a):
        main = self.get_main_config()
        if not a:
            return False
        object.__setattr__(main, "b", main.b.replace("normal", "a"))
        object.__setattr__(main.v, "vf", 1)

    def cpt(self, p):
        for t in p:
            self.cte(t)
        return p

    def csp(self, args):
        main = self.get_main_config()
        for arg in args:
            self.cte(t := arg.split(".")[0])
            if param := ".".join(arg.split(".")[1:]) not in main.a_config.ts[t].get_parameter_names():
                raise ValueError(f"Unknown parameter '{param}' of t '{t}'.")
        return args

    def cte(self, t):
        main = self.get_main_config()
        if t not in main.a_config.ts:
            raise ValueError("Unknown.")

    def do_a(self, ks):
        main = self.get_main_config()
        if not ks:
            return ks
        for phase in ["v", "te"]:
            for transform in ["t1", "t2"]:
                main.a_config[phase].pp.sp[f"{transform}.t1m"] = False
        return ks

    def parameters_pre_processing(self):
        return {
            "*_probability": self.check_number_in_range(0, 1),
            "a_config.ts.t3.m": self.check_number_in_range(minimum=0),
            "a_config.ts.t4.fr": self.check_param_in_list(VALID),
            "*_config_file": self.register_as_additional_config_file,
        }

    def parameters_post_processing(self):
        return {
            "a": self.a_f,
            "e": e,
            "a_config.a": self.do_a,
            "a_config.*.pp.p": self.cpt,
            "a_config.*.pp.sp": self.csp,
            "a_config.*.s": make_list,
            "t.tf": self.folder_in_experiment_if([("t.tn", True, bool), ("d", "t")]),
        }
