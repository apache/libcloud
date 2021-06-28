# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import re
import fnmatch

import setuptools
from setuptools import setup
from distutils.core import Command

try:
    import epydoc  # NOQA
    has_epydoc = True
except ImportError:
    has_epydoc = False

# NOTE: Those functions are intentionally moved in-line to prevent setup.py dependening on any
# Libcloud code which depends on libraries such as typing, enum, requests, etc.
# START: Taken From Twisted Python which licensed under MIT license
# https://github.com/powdahound/twisted/blob/master/twisted/python/dist.py
# https://github.com/powdahound/twisted/blob/master/LICENSE

# Names that are excluded from globbing results:
EXCLUDE_NAMES = ['{arch}', 'CVS', '.cvsignore', '_darcs',
                 'RCS', 'SCCS', '.svn']
EXCLUDE_PATTERNS = ['*.py[cdo]', '*.s[ol]', '.#*', '*~', '*.py']


def _filter_names(names):
    """
    Given a list of file names, return those names that should be copied.
    """
    names = [n for n in names
             if n not in EXCLUDE_NAMES]
    # This is needed when building a distro from a working
    # copy (likely a checkout) rather than a pristine export:
    for pattern in EXCLUDE_PATTERNS:
        names = [n for n in names
                 if not fnmatch.fnmatch(n, pattern) and not n.endswith('.py')]
    return names


def relative_to(base, relativee):
    """
    Gets 'relativee' relative to 'basepath'.

    i.e.,

    >>> relative_to('/home/', '/home/radix/')
    'radix'
    >>> relative_to('.', '/home/radix/Projects/Twisted')
    'Projects/Twisted'

    The 'relativee' must be a child of 'basepath'.
    """
    basepath = os.path.abspath(base)
    relativee = os.path.abspath(relativee)
    if relativee.startswith(basepath):
        relative = relativee[len(basepath):]
        if relative.startswith(os.sep):
            relative = relative[1:]
        return os.path.join(base, relative)
    raise ValueError("%s is not a subpath of %s" % (relativee, basepath))


def get_packages(dname, pkgname=None, results=None, ignore=None, parent=None):
    """
    Get all packages which are under dname. This is necessary for
    Python 2.2's distutils. Pretty similar arguments to getDataFiles,
    including 'parent'.
    """
    parent = parent or ""
    prefix = []
    if parent:
        prefix = [parent]
    bname = os.path.basename(dname)
    ignore = ignore or []
    if bname in ignore:
        return []
    if results is None:
        results = []
    if pkgname is None:
        pkgname = []
    subfiles = os.listdir(dname)
    abssubfiles = [os.path.join(dname, x) for x in subfiles]

    if '__init__.py' in subfiles:
        results.append(prefix + pkgname + [bname])
        for subdir in filter(os.path.isdir, abssubfiles):
            get_packages(subdir, pkgname=pkgname + [bname],
                         results=results, ignore=ignore,
                         parent=parent)
    res = ['.'.join(result) for result in results]
    return res


def get_data_files(dname, ignore=None, parent=None):
    """
    Get all the data files that should be included in this distutils Project.

    'dname' should be the path to the package that you're distributing.

    'ignore' is a list of sub-packages to ignore.  This facilitates
    disparate package hierarchies.  That's a fancy way of saying that
    the 'twisted' package doesn't want to include the 'twisted.conch'
    package, so it will pass ['conch'] as the value.

    'parent' is necessary if you're distributing a subpackage like
    twisted.conch.  'dname' should point to 'twisted/conch' and 'parent'
    should point to 'twisted'.  This ensures that your data_files are
    generated correctly, only using relative paths for the first element
    of the tuple ('twisted/conch/*').
    The default 'parent' is the current working directory.
    """
    parent = parent or "."
    ignore = ignore or []
    result = []
    for directory, subdirectories, filenames in os.walk(dname):
        resultfiles = []
        for exname in EXCLUDE_NAMES:
            if exname in subdirectories:
                subdirectories.remove(exname)
        for ig in ignore:
            if ig in subdirectories:
                subdirectories.remove(ig)
        for filename in _filter_names(filenames):
            resultfiles.append(filename)
        if resultfiles:
            for filename in resultfiles:
                file_path = os.path.join(directory, filename)
                if parent:
                    file_path = file_path.replace(parent + os.sep, '')
                result.append(file_path)

    return result
# END: Taken from Twisted


# Different versions of python have different requirements.  We can't use
# libcloud.utils.py3 here because it relies on backports dependency being
# installed / available
PY_pre_35 = sys.version_info < (3, 5, 0)

HTML_VIEWSOURCE_BASE = 'https://svn.apache.org/viewvc/libcloud/trunk'
PROJECT_BASE_DIR = 'https://libcloud.apache.org'
TEST_PATHS = ['libcloud/test', 'libcloud/test/common', 'libcloud/test/compute',
              'libcloud/test/storage', 'libcloud/test/loadbalancer',
              'libcloud/test/dns', 'libcloud/test/container',
              'libcloud/test/backup']
DOC_TEST_MODULES = ['libcloud.compute.drivers.dummy',
                    'libcloud.storage.drivers.dummy',
                    'libcloud.dns.drivers.dummy',
                    'libcloud.container.drivers.dummy',
                    'libcloud.backup.drivers.dummy']

SUPPORTED_VERSIONS = ['PyPy 3', 'Python 3.5+']

# NOTE: python_version syntax is only supported when build system has
# setuptools >= 36.2
# For installation, minimum required pip version is 1.4
# Reference: https://hynek.me/articles/conditional-python-dependencies/
INSTALL_REQUIREMENTS = [
    'requests>=2.5.0',
]

setuptools_version = tuple(setuptools.__version__.split(".")[0:2])
setuptools_version = tuple([int(c) for c in setuptools_version])

if setuptools_version < (36, 2):
    if 'bdist_wheel' in sys.argv:
        # NOTE: We need to do that because we use universal wheel
        msg = ('Need to use latest version of setuptools when building wheels to ensure included '
               'metadata is correct. Current version: %s' % (setuptools.__version__))
        raise RuntimeError(msg)

TEST_REQUIREMENTS = [
    'mock',
    'requests_mock',
    'pytest',
    'pytest-runner'
] + INSTALL_REQUIREMENTS

if PY_pre_35:
    version = '.'.join([str(x) for x in sys.version_info[:3]])
    print('Version ' + version + ' is not supported. Supported versions are: %s. '
          'Latest version which supports Python 2.7 and Python 3 < 3.5.0 is '
          'Libcloud v2.8.2' % ', '.join(SUPPORTED_VERSIONS))
    sys.exit(1)


def read_version_string():
    version = None
    cwd = os.path.dirname(os.path.abspath(__file__))
    version_file = os.path.join(cwd, 'libcloud/__init__.py')

    with open(version_file) as fp:
        content = fp.read()

    match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                      content, re.M)

    if match:
        version = match.group(1)
        return version

    raise Exception('Cannot find version in libcloud/__init__.py')


def forbid_publish():
    argv = sys.argv
    if 'upload'in argv:
        print('You shouldn\'t use upload command to upload a release to PyPi. '
              'You need to manually upload files generated using release.sh '
              'script.\n'
              'For more information, see "Making a release section" in the '
              'documentation')
        sys.exit(1)


class ApiDocsCommand(Command):
    description = "generate API documentation"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        if not has_epydoc:
            raise RuntimeError('Missing "epydoc" package!')

        os.system(
            'pydoctor'
            ' --add-package=libcloud'
            ' --project-name=libcloud'
            ' --make-html'
            ' --html-viewsource-base="%s"'
            ' --project-base-dir=`pwd`'
            ' --project-url="%s"'
            % (HTML_VIEWSOURCE_BASE, PROJECT_BASE_DIR))


forbid_publish()

needs_pytest = {'pytest', 'test', 'ptr'}.intersection(sys.argv)
pytest_runner = ['pytest-runner'] if needs_pytest else []

setup(
    name='apache-libcloud',
    version=read_version_string(),
    description='A standard Python library that abstracts away differences' +
                ' among multiple cloud provider APIs. For more information' +
                ' and documentation, please see https://libcloud.apache.org',
    long_description=open('README.rst').read(),
    author='Apache Software Foundation',
    author_email='dev@libcloud.apache.org',
    install_requires=INSTALL_REQUIREMENTS,
    python_requires=">=3.5.*, <4",
    packages=get_packages('libcloud'),
    package_dir={
        'libcloud': 'libcloud',
    },
    package_data={
        'libcloud': get_data_files('libcloud', parent='libcloud') + ['py.typed'],
    },
    license='Apache License (2.0)',
    url='https://libcloud.apache.org/',
    setup_requires=pytest_runner,
    tests_require=TEST_REQUIREMENTS,
    cmdclass={
        'apidocs': ApiDocsCommand,
    },
    zip_safe=False,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ]
)
