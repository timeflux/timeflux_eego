"""

"""
import collections
import enum

from timeflux.core.node import Node
import numpy as np
#import scipy.signal

import eego


class StandardConfig:
    def __init__(self, n_ref, n_bip, ref_range=1, bip_range=4):
        self.n_ref = n_ref
        self.n_bip = n_bip
        self.ref_range = ref_range
        self.bip_range = bip_range

    @property
    def ref_mask(self):
        return StandardConfig._mask(self.n_ref)

    @property
    def bip_mask(self):
        return StandardConfig._mask(self.n_bip)

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


def _verify_config(amp_type, channel_names, masks):
    pass


class EegoDriver(Node):

    def __init__(self, rate=512, reference_channels=None, bipolar_channels=None, amplifier_index=0):
        super().__init__()
        self._factory = eego._sdk.factory('eego-SDK.dll', None)
        self._amplifier = self._factory.amplifiers[amplifier_index]
        self._config = StandardConfig(16, 0)
        if rate not in self._amplifier.sampling_rates:
            raise ValueError(f'Unsupported sampling rate {rate} by {self._amplifier}')  # TODO: amplifier repr or str

        self._stream = self._amplifier.open_eeg_stream(rate,
                                                       self._config.ref_range,
                                                       self._config.bip_range,
                                                       reference_channels['mask'],
                                                       bipolar_channels['mask'])
        self._channel_names = (
            tuple(reference_channels['names']) +
            tuple(bipolar_channels['names']) +
            ('trigger', 'counter')
        )
        self.logger.info('Eeego amplifier connected %s', self._amplifier)
        #self._filter = scipy.signal.butter(6, 40, 'low', fs=512)
        #b, a = self._filter
        #self._zi = np.zeros((max(len(a), len(b)) - 1, len(self._channel_names)))

    def update(self):
        #self.logger.info('Updating')
        buffer = self._stream.get_data()
        #self.logger.info('Read %s', buffer.shape)
        n_samples, n_channels = buffer.shape
        if n_samples <= 0:
            return
        data = np.array(list(buffer))
        data = data.reshape(-1, n_channels)
        #b, a = self._filter
        #data, self._zi = scipy.signal.lfilter(b, a, data, axis=0, zi=self._zi)
        #data = data[::2, :]

        self.logger.info('Read data %s', data.shape)
        self.o_eeg.set(data, names=self._channel_names)
        self.o_eeg_resampled.set(data[::2, :], names=self._channel_names)
