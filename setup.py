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
import doctest

from distutils.core import setup
from distutils.core import Command
from unittest import TextTestRunner, TestLoader
from glob import glob
from subprocess import call
from os.path import splitext, basename, join as pjoin

try:
    import epydoc
    has_epydoc = True
except ImportError:
    has_epydoc = False

import libcloud.utils.misc
from libcloud.utils.dist import get_packages, get_data_files
from libcloud.utils.py3 import unittest2_required

libcloud.utils.misc.SHOW_DEPRECATION_WARNING = False


HTML_VIEWSOURCE_BASE = 'https://svn.apache.org/viewvc/libcloud/trunk'
PROJECT_BASE_DIR = 'http://libcloud.apache.org'
TEST_PATHS = ['libcloud/test', 'libcloud/test/common', 'libcloud/test/compute',
              'libcloud/test/storage', 'libcloud/test/loadbalancer',
              'libcloud/test/dns']
DOC_TEST_MODULES = ['libcloud.compute.drivers.dummy',
                    'libcloud.storage.drivers.dummy',
                    'libcloud.dns.drivers.dummy']

SUPPORTED_VERSIONS = ['2.5', '2.6', '2.7', 'PyPy', '3.x']

if sys.version_info <= (2, 4):
    version = '.'.join([str(x) for x in sys.version_info[:3]])
    print('Version ' + version + ' is not supported. Supported versions are ' +
          ', '.join(SUPPORTED_VERSIONS))
    sys.exit(1)

# pre-2.6 will need the ssl PyPI package
pre_python26 = (sys.version_info[0] == 2 and sys.version_info[1] < 6)


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


class TestCommand(Command):
    description = "run test suite"
    user_options = []

    def initialize_options(self):
        THIS_DIR = os.path.abspath(os.path.split(__file__)[0])
        sys.path.insert(0, THIS_DIR)
        for test_path in TEST_PATHS:
            sys.path.insert(0, pjoin(THIS_DIR, test_path))
        self._dir = os.getcwd()

    def finalize_options(self):
        pass

    def run(self):
        try:
            import mock
            mock
        except ImportError:
            print('Missing "mock" library. mock is library is needed '
                  'to run the tests. You can install it using pip: '
                  'pip install mock')
            sys.exit(1)

        if unittest2_required:
            try:
                import unittest2
                unittest2
            except ImportError:
                print('Python version: %s' % (sys.version))
                print('Missing "unittest2" library. unittest2 is library is '
                      'needed to run the tests. You can install it using pip: '
                      'pip install unittest2')
                sys.exit(1)

        status = self._run_tests()
        sys.exit(status)

    def _run_tests(self):
        secrets_current = pjoin(self._dir, 'libcloud/test', 'secrets.py')
        secrets_dist = pjoin(self._dir, 'libcloud/test', 'secrets.py-dist')

        if not os.path.isfile(secrets_current):
            print("Missing " + secrets_current)
            print("Maybe you forgot to copy it from -dist:")
            print("cp libcloud/test/secrets.py-dist libcloud/test/secrets.py")
            sys.exit(1)

        mtime_current = os.path.getmtime(secrets_current)
        mtime_dist = os.path.getmtime(secrets_dist)

        if mtime_dist > mtime_current:
            print("It looks like test/secrets.py file is out of date.")
            print("Please copy the new secrets.py-dist file over otherwise" +
                  " tests might fail")

        if pre_python26:
            missing = []
            # test for dependencies
            try:
                import simplejson
                simplejson              # silence pyflakes
            except ImportError:
                missing.append("simplejson")

            try:
                import ssl
                ssl                     # silence pyflakes
            except ImportError:
                missing.append("ssl")

            if missing:
                print("Missing dependencies: " + ", ".join(missing))
                sys.exit(1)

        testfiles = []
        for test_path in TEST_PATHS:
            for t in glob(pjoin(self._dir, test_path, 'test_*.py')):
                testfiles.append('.'.join(
                    [test_path.replace('/', '.'), splitext(basename(t))[0]]))

        tests = TestLoader().loadTestsFromNames(testfiles)

        for test_module in DOC_TEST_MODULES:
            tests.addTests(doctest.DocTestSuite(test_module))

        t = TextTestRunner(verbosity=2)
        res = t.run(tests)
        return not res.wasSuccessful()


class Pep8Command(Command):
    description = "run pep8 script"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            import pep8
            pep8
        except ImportError:
            print ('Missing "pep8" library. You can install it using pip: '
                   'pip install pep8')
            sys.exit(1)

        cwd = os.getcwd()
        retcode = call(('pep8 %s/libcloud/' %
                       (cwd)).split(' '))
        sys.exit(retcode)


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


class CoverageCommand(Command):
    description = "run test suite and generate coverage report"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import coverage
        cov = coverage.coverage(config_file='.coveragerc')
        cov.start()

        tc = TestCommand(self.distribution)
        tc._run_tests()

        cov.stop()
        cov.save()
        cov.html_report()

forbid_publish()

setup(
    name='apache-libcloud',
    version=read_version_string(),
    description='A standard Python library that abstracts away differences' +
                ' among multiple cloud provider APIs. For more information' +
                ' and documentation, please see http://libcloud.apache.org',
    author='Apache Software Foundation',
    author_email='dev@libcloud.apache.org',
    requires=([], ['ssl', 'simplejson'],)[pre_python26],
    packages=get_packages('libcloud'),
    package_dir={
        'libcloud': 'libcloud',
    },
    package_data={'libcloud': get_data_files('libcloud', parent='libcloud')},
    license='Apache License (2.0)',
    url='http://libcloud.apache.org/',
    cmdclass={
        'test': TestCommand,
        'pep8': Pep8Command,
        'apidocs': ApiDocsCommand,
        'coverage': CoverageCommand
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: Implementation :: PyPy'])
