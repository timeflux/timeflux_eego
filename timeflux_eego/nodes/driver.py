"""

"""

from timeflux.core.node import Node
import numpy as np

import eego


class EegoDriver(Node):

    def __init__(self, rate=512):
        super().__init__()
        self._factory = eego._sdk.factory()
        self._amplifier = self._factory.amplifier
        self._stream = self._amplifier.open_impedance_stream((1 << 24) - 1)

    def update(self):
        n_channels = len(self._stream.channels)
        data = np.array(list(self._stream.get_data())).reshape(-1, n_channels)
        self.o.set(data)
