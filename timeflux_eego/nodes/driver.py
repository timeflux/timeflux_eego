"""
"""
import time

from timeflux.core.node import Node
import numpy as np
import scipy.stats

import eego


class EegoDriver(Node):

    def __init__(self, dll_dir=None,
                 sampling_rate=512,
                 reference_channels=None, reference_range=1,
                 bipolar_channels=None, bipolar_range=4,
                 amplifier_index=0,
                 impedance_window=1):
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
        # self._channel_names = (
        #     self._ref_config.channels +
        #     self._bip_config.channels +
        #     ('trigger', 'counter')
        # )

        self._start_timestamp = None
        self._reference_ts = None
        self._sample_count = None
        self._impedance_window = impedance_window
        self._impedance_history = None

        self.logger.info('Eeego amplifier connected %s', self._amplifier)
        self._tmp = 512*5

    def update(self):
        if self._mode == 'eeg':
            self.update_signals()
        elif self._mode == 'impedance':
            self.update_impedances()

        # Handle events
        if self.i_events.data is not None and not self.i_events.data.empty:
            # TODO: use a self._trigger or something like that
            #self.logger.warning('GOT EVENT\n%s\nI am in %s', self.i_events.data, self._mode)
            start_impedance = np.any('pilote-Youpling-V1_eeg-impedance_begins' == self.i_events.data.label)
            start_eeg = np.any('pilote-Youpling-V1_eeg-impedance_ends' == self.i_events.data.label)

            if start_eeg and self._mode == 'impedance':
                self.logger.info('Switching to signal mode...')
                self._sample_count = None  # TODO: this is just for now
                del self._stream  # Important: this frees the device so we can make another stream
                self._stream = self._amplifier.open_eeg_stream(self._rate,
                                                               self._ref_config.range,
                                                               self._bip_config.range,
                                                               self._ref_config.mask,
                                                               self._bip_config.mask)
                self._mode = 'eeg'
                self._tmp = 512*5
            elif start_impedance and self._mode == 'eeg':
                self.logger.info('Switching to impedance mode...')
                self._impedance_history = None
                self._sample_count = None  # TODO: this is just for now
                del self._stream  # Important: this frees the device so we can make another stream
                self._stream = self._amplifier.open_impedance_stream(self._ref_config.mask)
                self._mode = 'impedance'
                self._tmp = 10

    def update_signals(self):
        #import ipdb; ipdb.set_trace()
        # The first time, drop all samples that might have been captured
        # between the initialization and the first time this is called
        if self._sample_count is None:
            buffer = self._stream.get_data()
            self.logger.info('Dropped a total of %d samples of data between '
                             'driver initializaion and first node update',
                             buffer.shape[0])
            self._start_timestamp = np.datetime64(int(time.time() * 1e6), 'us')
            self._reference_ts = self._start_timestamp
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

        # TODO: integrate/modify this from amti
        # # verify that there is no buffer overflow, but ignore the case when
        # # the counter rolls over (which is at 2^24 - 1, according to SDK on
        # # the fmDLLSetDataFormat function documentation)
        # idx = np.where(np.diff(data[:, 0]) != 1)[0]
        # if idx.size > 0 and np.any(data[idx, 0] != (2 ** 24 - 1)):
        #     self.logger.warning('Discontinuity on sample count. Check '
        #                         'your sampling rate and graph rate!')

        # sample counting to calculate drift
        self._sample_count += n_samples
        elapsed_seconds = (
                (np.datetime64(int(time.time() * 1e6), 'us') - self._reference_ts) /
                np.timedelta64(1, 's')
        )
        n_expected = int(np.round(elapsed_seconds * self._rate))
        # self.logger.debug('Read samples=%d, elapsed_seconds=%f. '
        #                  'Expected=%d Real=%d Diff=%d (%.3f sec)',
        #                  n_samples, elapsed_seconds,
        #                  n_expected, self._sample_count, n_expected - self._sample_count,
        #                  (n_expected - self._sample_count) / self._rate)

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

        self.logger.debug('Read %d samples of impedances', n_samples)
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
        #self.logger.info('impedance history is %s', self._impedance_history.shape)

        #avg_data = np.mean(self._impedance_history, axis=0)
        #avg_data = np.median(self._impedance_history, axis=0)  # median is more outlier-friendly
        avg_data = scipy.stats.gmean(self._impedance_history + 1e-3, axis=0)

        #self.logger.info('avg_data is %s', avg_data)
        #self.logger.info('avg_data shape is %s', avg_data.shape)
        #self.logger.info('names are %s', impedance_channel_names)

        self.o_eeg_impedance.set(avg_data[np.newaxis, :],
                                 names=impedance_channel_names)
        self.logger.info('Impedances (averaged over %d samples)\n%s',
                         self._impedance_window,
                         ' '.join([f'{ch}={val}'
                                   for ch, val in zip(impedance_channel_names, data[0])]))



import datetime


class FakeStimulator(Node):
    def __init__(self):
        super().__init__()
        self.time = datetime.datetime.now()
        self.mode = 'impedance'

    def update(self):
        now = datetime.datetime.now()
        if (now - self.time).total_seconds() > 10:
            self.time = now
            if self.mode == 'eeg':
                stim = 'pilote-Youpling-V1_eeg-impedance_begins'
                self.mode = 'impedance'
            else:
                stim = 'pilote-Youpling-V1_eeg-impedance_ends'
                self.mode = 'eeg'
            self.logger.info('Sending %s', stim)
            self.o_events.set([[stim, None]], names=['label', 'data'])
