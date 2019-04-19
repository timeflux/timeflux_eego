import enum
import functools

import eego.glue


# Extend pybind11 classes with Python logic
def add_method(cls, name=None):
    def decorator(func):
        @functools.wraps
        def wrapper(self, *args, **kwargs):
            return func(*args, **kwargs)
        setattr(cls, func.__name__, wrapper)
        return func
    return decorator

@add_method(eego.glue.amplifier, 'get_default_config')
def _default_config():
    print('getting default config!')
    return 1


class StandardConfig:

    def __init__(self, n_ref, n_bip, ref_range=1, bip_range=4):
        self.ref_count = n_ref
        self.ref_range = ref_range
        self.ref_mask = (1 << n_ref) - 1
        self.bip_range = bip_range
        self.bip_count = n_bip
        self.bip_mask = (1 << n_bip) - 1

    @staticmethod
    def from_amplifier(amplifier):
        pass

    # @property
    # def ref_mask(self):
    #     return StandardConfig._mask(self.n_ref)
    #
    # @property
    # def bip_mask(self):
    #     return StandardConfig._mask(self.n_bip)

    @staticmethod
    def _mask(n):
        return (1 << n) - 1


class EegoAmplifierConfig(enum.Enum):
    EE211 = StandardConfig(n_ref=64, n_bip=0)
    EE212 = StandardConfig(n_ref=32, n_bip=0)
    EE213 = StandardConfig(n_ref=16, n_bip=0)
    EE214 = StandardConfig(n_ref=32, n_bip=24)
    EE215 = StandardConfig(n_ref=64, n_bip=24)
    EE221 = StandardConfig(n_ref=16, n_bip=0)
    EE222 = StandardConfig(n_ref=32, n_bip=0)
    EE223 = StandardConfig(n_ref=32, n_bip=24)
    EE224 = StandardConfig(n_ref=64, n_bip=0)
    EE225 = StandardConfig(n_ref=64, n_bip=24)
    EE410 = StandardConfig(n_ref=8, n_bip=0)
    EE411 = StandardConfig(n_ref=8, n_bip=0)
    EE430 = StandardConfig(n_ref=8, n_bip=0)

    @staticmethod
    def get_config(amplifier_name):
        if hasattr(StandardConfig, amplifier_name):
            return getattr(StandardConfig, amplifier_name)
        raise AttributeError(f'Unknown amplifier {amplifier_name}: no default config available')

