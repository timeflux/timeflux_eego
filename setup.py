from setuptools import find_packages, setup, Extension
from setuptools.command.build_ext import build_ext
import os
import sys
import setuptools
import warnings

__version__ = '0.1.0'


class get_pybind_include(object):
    """Helper class to determine the pybind11 include path

    The purpose of this class is to postpone importing pybind11
    until it is actually installed, so that the ``get_include()``
    method can be invoked. """

    def __init__(self, user=False):
        self.user = user

    def __str__(self):
        import pybind11
        return pybind11.get_include(self.user)


ext_modules = [
    Extension(
        'eego.glue',
        [
            'eego/glue.cpp',
        ],
        include_dirs=[
            # Path to pybind11 headers
            get_pybind_include(),
            get_pybind_include(user=True),
            'eego',
        ],
        language='c++',
    ),
]


# As of Python 3.6, CCompiler has a `has_flag` method.
# cf http://bugs.python.org/issue26689
def has_flag(compiler, flagname):
    """Return a boolean indicating whether a flag name is supported on
    the specified compiler.
    """
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.cpp') as f:
        f.write('int main (int argc, char **argv) { return 0; }')
        try:
            compiler.compile([f.name], extra_postargs=[flagname])
        except setuptools.distutils.errors.CompileError:
            return False
    return True


def cpp_flag(compiler):
    """Return the -std=c++[11/14] compiler flag.

    The c++14 is prefered over c++11 (when it is available).
    """
    if has_flag(compiler, '-std=c++14'):
        return '-std=c++14'
    elif has_flag(compiler, '-std=c++11'):
        return '-std=c++11'
    else:
        raise RuntimeError('Unsupported compiler -- at least C++11 support '
                           'is needed!')


class BuildExt(build_ext):
    """A custom build extension for adding compiler-specific options."""
    c_opts = {
        'msvc': ['/EHsc'],
        'unix': [],
    }

    if sys.platform == 'darwin':
        if os.environ.get('MACOSX_DEPLOYMENT_TARGET') != '10.9':
            warnings.warn('Compiling pybind11 wrapper with OSX is only '
                          'supported if the environment variable '
                          'MACOSX_DEPLOYMENT_TARGET is set to "10.9"',
                          UserWarning)
        c_opts['unix'] += ['-stdlib=libc++', '-mmacosx-version-min=10.9', '-D__unix__']

    def build_extensions(self):
        ct = self.compiler.compiler_type
        opts = self.c_opts.get(ct, [])
        if ct == 'unix':
            opts.append('-DVERSION_INFO="%s"' % self.distribution.get_version())
            opts.append(cpp_flag(self.compiler))
            if has_flag(self.compiler, '-fvisibility=hidden'):
                opts.append('-fvisibility=hidden')
        elif ct == 'msvc':
            opts.append('/DVERSION_INFO=\\"%s\\"' % self.distribution.get_version())
            opts.append('/DEEGO_SDK_BIND_DYNAMIC')
            opts.append('/D_UNICODE')
        for ext in self.extensions:
            ext.extra_compile_args = opts
        build_ext.build_extensions(self)


requirements = [
    'pybind11>=2.2',
    'numpy',
    'frozendict',
    'timeflux @ git+https://github.com/timeflux/timeflux#egg=timeflux',
]
setup_requirements = ['pytest-runner', ]
test_requirements = ['pytest', ]

setup(
    author='Timeflux',
    author_email='',
    name='timeflux_eego',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description='',
    install_requires=requirements,
    license="MIT license",
    include_package_data=True,
    packages=find_packages(exclude=['doc', 'test']),
    ext_modules=ext_modules,
    cmdclass={'build_ext': BuildExt},
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/timeflux/timeflux_eego',
    version=__version__,
    zip_safe=False,
)
