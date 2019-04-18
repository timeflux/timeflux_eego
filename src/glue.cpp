#include <sstream>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "eemagine/sdk/channel.h"
#include "eemagine/sdk/amplifier.h"
#include "eemagine/sdk/stream.h"
#include "eemagine/sdk/factory.h"
#include "eemagine/sdk/wrapper.cc"


// synonym pybind11 for shorter code
namespace py = pybind11;

// Python-C++ bindings using pybind11
PYBIND11_MODULE(eego, base_module) {
    //m.doc() = "eego_sdk docstring";
    py::module _sm = base_module.def_submodule("_sdk", "Submodule _sdk");

    // eego._sdk.channel_type
    py::enum_<eemagine::sdk::channel::channel_type>(_sm, "channel_type")
        .value("none",                eemagine::sdk::channel::channel_type::none)
        .value("reference",           eemagine::sdk::channel::channel_type::reference)
        .value("bipolar",             eemagine::sdk::channel::channel_type::bipolar)
        .value("trigger",             eemagine::sdk::channel::channel_type::trigger)
        .value("sample_counter",      eemagine::sdk::channel::channel_type::sample_counter)
        .value("impedance_reference", eemagine::sdk::channel::channel_type::impedance_reference)
        .value("impedance_ground",    eemagine::sdk::channel::channel_type::impedance_ground)
        .value("accelerometer",       eemagine::sdk::channel::channel_type::accelerometer)
        .value("gyroscope",           eemagine::sdk::channel::channel_type::gyroscope)
        .value("magnetometer",        eemagine::sdk::channel::channel_type::magnetometer);

    // eego._sdk.channel
    py::class_<eemagine::sdk::channel>(_sm, "channel")
        .def_property_readonly("index", &eemagine::sdk::channel::getIndex)
        .def_property_readonly("type", &eemagine::sdk::channel::getType)
        .def("__repr__", [](const eemagine::sdk::channel& ch) {
            // use operator<< defined in channel.h
            std::ostringstream os;
            os << ch;
            return os.str();
        });

    // eego._sdk.buffer
    py::class_<eemagine::sdk::buffer>(_sm, "buffer")
        .def_property_readonly("channel_count", &eemagine::sdk::buffer::getChannelCount)
        .def_property_readonly("sample_count",  &eemagine::sdk::buffer::getSampleCount)
        .def_property_readonly("shape", [](const eemagine::sdk::buffer& buf) {
            return py::make_tuple(buf.getSampleCount(), buf.getChannelCount());
        })
        .def("__len__", [](const eemagine::sdk::buffer &b) {
            return b.size();
        })
        .def("__iter__", [](const eemagine::sdk::buffer &b) {
            auto base_address(&b.getSample(0, 0));
            return py::make_iterator(base_address,
                base_address + b.size());
            },
            py::keep_alive<0, 1>());

    // eego._sdk.stream
    py::class_<eemagine::sdk::stream>(_sm, "stream")
        .def_property_readonly("channels", &eemagine::sdk::stream::getChannelList)
        .def("get_data", &eemagine::sdk::stream::getData);

    // eego._sdk.amplifier
    //py::class_<eemagine::sdk::amplifier>(_sm, "amplifier")
    py::class_<eemagine::sdk::amplifier>(_sm, "amplifier")
        .def_property_readonly("type",              &eemagine::sdk::amplifier::getType)
        .def_property_readonly("firmware_version",  &eemagine::sdk::amplifier::getFirmwareVersion)
        .def_property_readonly("serial_number",     &eemagine::sdk::amplifier::getSerialNumber)
        .def_property_readonly("channels",          &eemagine::sdk::amplifier::getChannelList)
        .def_property_readonly("reference_ranges",  &eemagine::sdk::amplifier::getReferenceRangesAvailable)
        .def_property_readonly("bipolar_ranges",    &eemagine::sdk::amplifier::getBipolarRangesAvailable)
        .def("open_eeg_stream",                     &eemagine::sdk::amplifier::OpenEegStream)
        .def("open_impedance_stream",               &eemagine::sdk::amplifier::OpenImpedanceStream);

    // eego._sdk.factory.version
    py::class_<eemagine::sdk::factory::version>(_sm, "factory.version")
        .def_readonly("major", &eemagine::sdk::factory::version::major)
        .def_readonly("minor", &eemagine::sdk::factory::version::minor)
        .def_readonly("micro", &eemagine::sdk::factory::version::micro)
        .def_readonly("build", &eemagine::sdk::factory::version::build)
        .def("__repr__", [](const eemagine::sdk::factory::version& v) {
            return
                "factory.version(major=" + std::to_string(v.major) +
                ", minor=" + std::to_string(v.minor) +
                ", micro=" + std::to_string(v.micro) +
                ", build=" + std::to_string(v.build) + ")";
        })
        .def("__str__", [](const eemagine::sdk::factory::version& v) {
            return
                std::to_string(v.major) + "." +
                std::to_string(v.minor) + "." +
                std::to_string(v.micro) + "." +
                std::to_string(v.build);
        });

    // eego._sdk.factory
    py::class_<eemagine::sdk::factory>(_sm, "factory")
#ifdef EEGO_SDK_BIND_STATIC
        .def(py::init<void *>())
#else
#ifdef _WIN32
        .def(py::init<const std::wstring&, void *>())
#endif
        .def(py::init<const std::string&, void *>())
#endif // EEGO_SDK_BIND_STATIC
        .def_property_readonly("version", &eemagine::sdk::factory::getVersion)
        .def_property_readonly("amplifier",  &eemagine::sdk::factory::getAmplifier)
        .def_property_readonly("amplifiers", &eemagine::sdk::factory::getAmplifiers)
        .def("__repr__",
            [](const eemagine::sdk::factory& f) {
                return "<repr of factory>";
         });
}
