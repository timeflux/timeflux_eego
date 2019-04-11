#include <pybind11/pybind11.h>

//namespace py = pybind11;

// pybind
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
// sdk
#include <eemagine/sdk/amplifier.h>
#include <eemagine/sdk/channel.h>
#include <eemagine/sdk/factory.h>
#include <eemagine/sdk/stream.h>
#include <eemagine/sdk/wrapper.cc>
///////////////////////////////////////////////////////////////////////////////
#if (EEGO_SDK_VERSION >= 46273)
#define HAVE_CASCADING
#endif
///////////////////////////////////////////////////////////////////////////////
namespace {
//
std::ostream &operator<<(std::ostream &out,
                         const eemagine::sdk::channel::channel_type &t) {
  switch (t) {
  case eemagine::sdk::channel::channel_type::none:
    out << "none";
    break;
  case eemagine::sdk::channel::channel_type::reference:
    out << "ref";
    break;
  case eemagine::sdk::channel::channel_type::bipolar:
    out << "bip";
    break;
  case eemagine::sdk::channel::channel_type::trigger:
    out << "trg";
    break;
  case eemagine::sdk::channel::channel_type::sample_counter:
    out << "sc";
    break;
  case eemagine::sdk::channel::channel_type::impedance_reference:
    out << "ir";
    break;
  case eemagine::sdk::channel::channel_type::impedance_ground:
    out << "ig";
    break;
  case eemagine::sdk::channel::channel_type::accelerometer:
    out << "acc";
    break;
  case eemagine::sdk::channel::channel_type::gyroscope:
    out << "gyr";
    break;
  case eemagine::sdk::channel::channel_type::magnetometer:
    out << "mag";
    break;
  }
  return out;
}

//
// amplifier_wrapper
//
class amplifier_wrapper : public eemagine::sdk::amplifier {
public:
  eemagine::sdk::stream *OpenEegStream_nomask(int rate, double ref_range,
                                              double bip_range) {
    return OpenEegStream(rate, ref_range, bip_range);
  }
  eemagine::sdk::stream *OpenImpedanceStream_nomask() {
    return OpenImpedanceStream();
  }
};

//
// factory_wrapper
//
class factory_wrapper {
public:
  eemagine::sdk::factory::version getVersion() const {
    return _factory.getVersion();
  }

  amplifier_wrapper *getAmplifier() {
    return static_cast<amplifier_wrapper *>(_factory.getAmplifier());
  }
  std::vector<amplifier_wrapper *> getAmplifiers() {
    std::vector<amplifier_wrapper *> rv;
    for (auto *a : _factory.getAmplifiers()) {
      rv.push_back(static_cast<amplifier_wrapper *>(a));
    }
    return rv;
  }

#ifdef HAVE_CASCADING
  amplifier_wrapper *createCascadedAmplifier(pybind11::list python_list) {
    std::vector<eemagine::sdk::amplifier *> amplifier_list;
    for (auto p : python_list) {
      amplifier_list.push_back(p.cast<amplifier_wrapper *>());
    }
    return static_cast<amplifier_wrapper *>(
        _factory.createCascadedAmplifier(amplifier_list));
  }
#endif

private:
  eemagine::sdk::factory _factory;
};
} // namespace
///////////////////////////////////////////////////////////////////////////////
PYBIND11_MODULE(eego_sdk, m) {
  //
  // channel type
  //
  pybind11::enum_<eemagine::sdk::channel::channel_type>(m, "channel_type")
      .value("none", eemagine::sdk::channel::channel_type::none)
      .value("ref", eemagine::sdk::channel::channel_type::reference)
      .value("bip", eemagine::sdk::channel::channel_type::bipolar)
      .value("trg", eemagine::sdk::channel::channel_type::trigger)
      .value("sc", eemagine::sdk::channel::channel_type::sample_counter)
      .value("ir", eemagine::sdk::channel::channel_type::impedance_reference)
      .value("ig", eemagine::sdk::channel::channel_type::impedance_ground)
      .value("acc", eemagine::sdk::channel::channel_type::accelerometer)
      .value("gyr", eemagine::sdk::channel::channel_type::gyroscope)
      .value("mag", eemagine::sdk::channel::channel_type::magnetometer);

  //
  // channel
  //
  pybind11::class_<eemagine::sdk::channel>(m, "channel")
      .def("getIndex", &eemagine::sdk::channel::getIndex)
      .def("getType", &eemagine::sdk::channel::getType)
      .def("__repr__", [](const eemagine::sdk::channel &c) {
        std::ostringstream os;
        os << "channel(" << c.getIndex() << ", " << c.getType() << ")";
        return os.str();
      });

  //
  // buffer
  //
  pybind11::class_<eemagine::sdk::buffer>(m, "buffer")
      .def("getChannelCount", &eemagine::sdk::buffer::getChannelCount)
      .def("getSampleCount", &eemagine::sdk::buffer::getSampleCount)
      .def("getSample", &eemagine::sdk::buffer::getSample)
      .def("__len__", [](const eemagine::sdk::buffer &b) { return b.size(); })
      .def("__iter__",
           [](const eemagine::sdk::buffer &b) {
             auto base_address(&b.getSample(0, 0));
             return pybind11::make_iterator(base_address,
                                            base_address + b.size());
           },
           pybind11::keep_alive<0, 1>());

  //
  // stream
  //
  pybind11::class_<eemagine::sdk::stream>(m, "stream")
      .def("getChannelList", &eemagine::sdk::stream::getChannelList)
      .def("getData", &eemagine::sdk::stream::getData);

  //
  // amplifier
  //
  pybind11::class_<amplifier_wrapper>(m, "amplifier")
      .def("getType", &amplifier_wrapper::getType)
      .def("getFirmwareVersion", &amplifier_wrapper::getFirmwareVersion)
      .def("getSerialNumber", &amplifier_wrapper::getSerialNumber)
      .def("OpenEegStream", &amplifier_wrapper::OpenEegStream_nomask)
      .def("OpenImpedanceStream",
           &amplifier_wrapper::OpenImpedanceStream_nomask)
      .def("getChannelList", &amplifier_wrapper::getChannelList)
      .def("getSamplingRatesAvailable",
           &amplifier_wrapper::getSamplingRatesAvailable)
      .def("getReferenceRangesAvailable",
           &amplifier_wrapper::getReferenceRangesAvailable)
      .def("getBipolarRangesAvailable",
           &amplifier_wrapper::getBipolarRangesAvailable);

  //
  // factory version
  //
  pybind11::class_<eemagine::sdk::factory::version>(m, "factory.version")
      .def_readonly("major", &eemagine::sdk::factory::version::major)
      .def_readonly("minor", &eemagine::sdk::factory::version::minor)
      .def_readonly("micro", &eemagine::sdk::factory::version::micro)
      .def_readonly("build", &eemagine::sdk::factory::version::build);

  //
  // factory
  //
  pybind11::class_<factory_wrapper>(m, "factory")
      .def(pybind11::init<>())
      .def("getVersion", &factory_wrapper::getVersion)
      .def("getAmplifier", &factory_wrapper::getAmplifier)
      .def("getAmplifiers", &factory_wrapper::getAmplifiers)
#ifdef HAVE_CASCADING
      .def("createCascadedAmplifier", &factory_wrapper::createCascadedAmplifier)
#endif
      ;
}
