"""
"""
import time

from timeflux.core.node import Node
import numpy as np
import scipy.stats

import eego


class EegoDriver(Node):

    def __init__(self,
                 dll_dir=None,
                 sampling_rate=512,
                 reference_channels=None,
                 reference_range=1,
                 bipolar_channels=None,
                 bipolar_range=4,
                 amplifier_index=0,
                 impedance_window=1,
                 start_impedance_trigger=None,
                 start_eeg_trigger=None,
                 trigger_column='label'):
        super().__init__()
        self._factory = eego.glue.factory(dll_dir or eego.sdk.default_dll(), None)
        retries = 3
        self._amplifier = None
        while retries > 0:
            retries -= 1
            try:
                self._amplifier = self._factory.amplifiers[amplifier_index]
            except IndexError:
                self.logger.warning('Amplifier %d not found, retrying...', amplifier_index)
                time.sleep(1)
            if self._amplifier:
                self.logger.info('Connected to amplifier')
                break
        if not self._amplifier:
            self.logger.error('Could not find EEG amplifier, is it connected and on?')
            raise ValueError('Could not initialize EEG amplifier')
        self._ref_config = self._amplifier.get_default_config('reference',
                                                              names=reference_channels,
                                                              signal_range=reference_range)
        self._bip_config = self._amplifier.get_default_config('bipolar',
                                                              names=bipolar_channels,
                                                              signal_range=bipolar_range)
        if sampling_rate not in self._amplifier.sampling_rates:
            raise ValueError(f'Unsupported sampling rate {sampling_rate} by '
                             f'{self._amplifier}')  # TODO: amplifier repr or str
        self._rate = sampling_rate

        self._mode = 'eeg'
        self.logger.info('Masks are %x %x', self._bip_config.mask, self._ref_config.mask)
        self._stream = self._amplifier.open_eeg_stream(self._rate,
                                                       self._ref_config.range,
                                                       self._bip_config.range,
                                                       self._ref_config.mask,
                                                       self._bip_config.mask)
        self._start_impedance_trigger = start_impedance_trigger
        self._start_eeg_trigger = start_eeg_trigger
        self._trigger_column = trigger_column

        self._start_timestamp = None
        self._reference_ts = None
        self._sample_count = None
        self._impedance_window = impedance_window
        self._impedance_history = None

        self.logger.info('Eeego amplifier connected %s', self._amplifier)

    def update(self):
        if self._mode == 'eeg':
            self.update_signals()
        elif self._mode == 'impedance':
            self.update_impedances()

        # Handle events
        if self.i_events.ready():
            start_impedance = (
                self._start_impedance_trigger is not None and
                np.any(self._start_impedance_trigger == self.i_events.data[self._trigger_column])
            )
            start_eeg = (
                self._start_eeg_trigger is not None and
                np.any(self._start_eeg_trigger == self.i_events.data[self._trigger_column])
            )

            if start_eeg and self._mode == 'impedance':
                self.logger.info('Switching to signal mode...')
                self._sample_count = None
                del self._stream  # Important: this frees the device so we can make another stream
                self._stream = self._amplifier.open_eeg_stream(self._rate,
                                                               self._ref_config.range,
                                                               self._bip_config.range,
                                                               self._ref_config.mask,
                                                               self._bip_config.mask)
                self._mode = 'eeg'

            elif start_impedance and self._mode == 'eeg':
                self.logger.info('Switching to impedance mode...')
                self._impedance_history = None
                self._sample_count = None
                del self._stream  # Important: this frees the device so we can make another stream
                self._stream = self._amplifier.open_impedance_stream(self._ref_config.mask)
                self._mode = 'impedance'

    def update_signals(self):
        # The first time, drop all samples that might have been captured
        # between the initialization and the first time this is called
        if self._sample_count is None:
            buffer = self._stream.get_data()
            n_samples, n_channels = buffer.shape
            self.logger.info('Dropped a total of %d samples of data between '
                             'driver initialization and first node update',
                             n_samples)
            self._sample_count = 0

        try:
            buffer = self._stream.get_data()
        except RuntimeError as ex:
            self.logger.error('Eego SDK gave runtime error (%s), '
                              'resuming the driver acquisition...', ex)
            return
        n_samples, n_channels = buffer.shape
        if n_samples <= 0:
            self.logger.info('No data yet...')
            return

        data = np.fromiter(buffer, dtype=np.float).reshape(-1, n_channels)
        del buffer

        # account for read data for starting timestamp
        if self._sample_count == 0 and n_samples > 0:
            self._start_timestamp = (
                np.datetime64(int(time.time() * 1e6), 'us') -
                # Adjust for the read samples
                int(1e6 * n_samples / self._rate)
            )
            self._reference_ts = self._start_timestamp

        # sample counting to calculate drift
        self._sample_count += n_samples
        elapsed_seconds = (
                (np.datetime64(int(time.time() * 1e6), 'us') - self._reference_ts) /
                np.timedelta64(1, 's')
        )
        n_expected = int(np.round(elapsed_seconds * self._rate))
        self.logger.debug('Read samples=%d, elapsed_seconds=%f. '
                          'Expected=%d Real=%d Diff=%d (%.3f sec)',
                          n_samples, elapsed_seconds,
                          n_expected, self._sample_count, n_expected - self._sample_count,
                          (n_expected - self._sample_count) / self._rate)

        # Manage timestamps
        # For this node, we are trusting the device clock and setting the
        # timestamps from the sample number and sampling rate
        timestamps = (
                self._start_timestamp +
                (np.arange(n_samples + 1) * 1e6 / self._rate).astype('timedelta64[us]')
        )
        self._start_timestamp = timestamps[-1]

        eeg_channels = self._ref_config.channels + ('trigger', 'counter')
        eeg_col_idx = np.r_[np.arange(len(self._ref_config.channels)), [-2, -1]]
        self.o_eeg_signal.set(data[:, eeg_col_idx],
                              timestamps=timestamps[:-1],
                              names=eeg_channels)

        bip_channels = self._bip_config.channels + ('trigger', 'counter')
        bip_col_idx = np.r_[np.arange(len(self._bip_config.channels)) + len(self._ref_config.channels),
                            [-2, -1]]
        self.o_bipolar_signal.set(data[:, bip_col_idx],
                                  timestamps=timestamps[:-1],
                                  names=bip_channels)

    def update_impedances(self):
        buffer = self._stream.get_data()
        n_samples, n_channels = buffer.shape
        if n_samples <= 0:
            return

        data = np.fromiter(buffer, dtype=np.float).reshape(-1, n_channels)
        del buffer
        self._sample_count = self._sample_count or 0
        self._sample_count += n_samples
        impedance_channel_names = self._ref_config.channels + ('REF', 'GND')

        # Manage window
        if self._impedance_history is None:
            self._impedance_history = data
        else:
            self._impedance_history = np.r_[self._impedance_history, data][-self._impedance_window:]

        avg_data = scipy.stats.gmean(self._impedance_history + 1e-3, axis=0)

        self.o_eeg_impedance.set(avg_data[np.newaxis, :],
                                 names=impedance_channel_names)