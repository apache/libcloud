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

from setuptools import setup
from distutils.core import Command
from os.path import join as pjoin

try:
    import epydoc  # NOQA
    has_epydoc = True
except ImportError:
    has_epydoc = False


import libcloud.utils  # NOQA
from libcloud.utils.dist import get_packages, get_data_files  # NOQA

libcloud.utils.SHOW_DEPRECATION_WARNING = False

# Different versions of python have different requirements.  We can't use
# libcloud.utils.py3 here because it relies on backports dependency being
# installed / available
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
PY3_pre_34 = PY3 and sys.version_info < (3, 4)
PY2_pre_26 = PY2 and sys.version_info < (2, 6)
PY2_pre_27 = PY2 and sys.version_info < (2, 7)
PY2_pre_279 = PY2 and sys.version_info < (2, 7, 9)

HTML_VIEWSOURCE_BASE = 'https://svn.apache.org/viewvc/libcloud/trunk'
PROJECT_BASE_DIR = 'http://libcloud.apache.org'
TEST_PATHS = ['libcloud/test', 'libcloud/test/common', 'libcloud/test/compute',
              'libcloud/test/storage', 'libcloud/test/loadbalancer',
              'libcloud/test/dns', 'libcloud/test/container',
              'libcloud/test/backup']
DOC_TEST_MODULES = ['libcloud.compute.drivers.dummy',
                    'libcloud.storage.drivers.dummy',
                    'libcloud.dns.drivers.dummy',
                    'libcloud.container.drivers.dummy',
                    'libcloud.backup.drivers.dummy']

SUPPORTED_VERSIONS = ['2.6', '2.7', 'PyPy', '3.x']

TEST_REQUIREMENTS = [
    'mock',
    'requests',
    'requests_mock',
    'pytest',
    'pytest-runner'
]

if PY2_pre_279:
    TEST_REQUIREMENTS.append('backports.ssl_match_hostname')

if PY2_pre_27 or PY3_pre_34:
    version = '.'.join([str(x) for x in sys.version_info[:3]])
    print('Version ' + version + ' is not supported. Supported versions are ' +
          ', '.join(SUPPORTED_VERSIONS))
    sys.exit(1)


def read_version_string():
    version = None
    sys.path.insert(0, pjoin(os.getcwd()))
    from libcloud import __version__
    version = __version__
    sys.path.pop(0)
    return version


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

install_requires = ['requests']

if PY2_pre_279:
    install_requires.append('backports.ssl_match_hostname')

needs_pytest = {'pytest', 'test', 'ptr'}.intersection(sys.argv)
pytest_runner = ['pytest-runner'] if needs_pytest else []

setup(
    name='apache-libcloud',
    version=read_version_string(),
    description='A standard Python library that abstracts away differences' +
                ' among multiple cloud provider APIs. For more information' +
                ' and documentation, please see http://libcloud.apache.org',
    author='Apache Software Foundation',
    author_email='dev@libcloud.apache.org',
    install_requires=install_requires,
    packages=get_packages('libcloud'),
    package_dir={
        'libcloud': 'libcloud',
    },
    package_data={'libcloud': get_data_files('libcloud', parent='libcloud')},
    license='Apache License (2.0)',
    url='http://libcloud.apache.org/',
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
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ]
)
