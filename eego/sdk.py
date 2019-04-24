import collections
import pathlib
import sys
import warnings

from frozendict import frozendict

import eego
import eego.glue


def default_dll():
    if sys.platform == 'win32':
        os_dirname = 'windows'
        lib_name = 'eego-SDK.dll'
    elif sys.platform == 'linux':
        os_dirname = 'linux'
        lib_name = 'libeego-SDK.so'
    else:
        warnings.warn(f'Platform {sys.platform} is not supported.',
                      UserWarning, stacklevel=2)
        return None

    if sys.maxsize > 2 ** 32:
        size_dir = '64bit'
    else:
        size_dir = '32bit'

    base_path = pathlib.Path(eego.__file__).parent  # <install_dir>/eego
    path = (base_path / os_dirname / size_dir / lib_name).resolve()
    return str(path)


class AmplifierConfig:

    def __init__(self, n_ref, n_bip):
        self.n_ref = n_ref
        self.n_bip = n_bip


EegoAmplifiers = frozendict(
    EE211=AmplifierConfig(n_ref=64, n_bip=0),
    EE212=AmplifierConfig(n_ref=32, n_bip=0),
    EE213=AmplifierConfig(n_ref=16, n_bip=0),
    EE214=AmplifierConfig(n_ref=32, n_bip=24),
    EE215=AmplifierConfig(n_ref=64, n_bip=24),
    EE221=AmplifierConfig(n_ref=16, n_bip=0),
    EE222=AmplifierConfig(n_ref=32, n_bip=0),
    EE223=AmplifierConfig(n_ref=32, n_bip=24),
    EE224=AmplifierConfig(n_ref=64, n_bip=0),
    EE225=AmplifierConfig(n_ref=64, n_bip=24),
    EE410=AmplifierConfig(n_ref=8, n_bip=0),
    EE411=AmplifierConfig(n_ref=8, n_bip=0),
    EE430=AmplifierConfig(n_ref=8, n_bip=0),
)


# Extend pybind11 classes with Python logic
def add_method(cls, name=None):
    def decorator(func):
        setattr(cls, name or func.__name__, func)
        return func
    return decorator


_config_type = collections.namedtuple('Config', ['mask', 'range', 'channels'])


@add_method(eego.glue.amplifier, 'get_default_config')
def get_config(self, channel_type, *, names=None, signal_range=None):
    # Verify channel type
    if channel_type not in {'reference', 'bipolar'}:
        raise ValueError(f'Unknown channel type "{channel_type}"')

    # Get the known configurations from the amplifier identifier
    default_config = EegoAmplifiers.get(self.type, None)
    if default_config is None:
        raise ValueError(f'Unknown amplifier {self.type}')

    # Check the number of channels with respect to known amplifiers and
    # that the signal ranges are supported
    if channel_type == 'reference':
        max_channels = default_config.n_ref
        known_ranges = self.reference_ranges
    else:
        max_channels = default_config.n_bip
        known_ranges = self.bipolar_ranges

    # number of channels
    names = names or [f'{channel_type[:3]}_{i}' for i in range(max_channels)]
    if len(names) > max_channels:
        raise ValueError(f'Amplifier {self.type} only supports '
                         f'{max_channels} {channel_type} channels, '
                         f'but user configuration has {len(names)} channels.')

    # signal ranges
    signal_range = signal_range or max(known_ranges)
    if signal_range not in known_ranges:
        raise ValueError(f'Amplifier {self.type} does not support '
                         f'{channel_type} range {signal_range}.')

    # Create a mask from the configuration
    mask_array = (
        [str(int(ch is not None)) for ch in names] +  # list of "0" or "1" according to existence of channel name
        ['0'] * (max_channels - len(names))       # pad "0" to the right to complete mask
    )
    mask = int(''.join(mask_array[::-1]), base=2)  # inverse the mask order and convert to binary

    # Build the channel name tuple
    channels = tuple(ch for ch in names if ch is not None)

    return _config_type(mask, signal_range, channels)
