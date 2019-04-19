import eego


def test_eego_glue_definitions():
    """Verify the expected symbols defined in pybind11"""
    pybind11_classes = (
        'factory', 'factory.version',
        'amplifier',
        'channel', 'channel_type',
        'buffer', 'stream',
    )
    for cls in pybind11_classes:
        assert hasattr(eego.glue, cls)


# def test_channel_type():
#     """Test channel type enumeration bindings"""
#     known_channel_types = {
#         'none', 'reference', 'bipolar', 'trigger', 'sample_counter',
#         'impedance_reference', 'impedance_ground', 'accelerometer',
#         'gyroscope', 'magnetometer',
#     }
#     for ch in known_channel_types:
#         assert hasattr(eego.glue.channel_type, ch)
#         assert isinstance(getattr(eego.glue.channel_type, ch), eego.glue.channel_type)


