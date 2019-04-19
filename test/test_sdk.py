import sys

import pytest

import eego


@pytest.mark.skipif(sys.platform not in {'win32', 'linux'},
                    reason='Only windows and linux are supported')
def test_default_dll():
    """The default driver should load correctly"""
    dll = eego.sdk.default_dll()
    factory = eego.glue.factory(dll, None)
    # the line before should not raise an exception, but just in case it is
    # secretly handled, at least factory should not be None
    assert factory is not None
