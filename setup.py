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

import libcloud.utils.misc
libcloud.utils.misc.SHOW_DEPRECATION_WARNING = False


HTML_VIEWSOURCE_BASE = 'https://svn.apache.org/viewvc/libcloud/trunk'
PROJECT_BASE_DIR = 'http://libcloud.apache.org'
TEST_PATHS = ['test', 'test/common', 'test/compute', 'test/storage',
              'test/loadbalancer', 'test/dns']
DOC_TEST_MODULES = ['libcloud.compute.drivers.dummy',
                     'libcloud.storage.drivers.dummy',
                     'libcloud.dns.drivers.dummy']

SUPPORTED_VERSIONS = ['2.5', '2.6', '2.7', 'PyPy', '3.x']

if sys.version_info <= (2, 4):
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

        status = self._run_tests()
        sys.exit(status)

    def _run_tests(self):
        secrets = pjoin(self._dir, 'test', 'secrets.py')
        if not os.path.isfile(secrets):
            print("Missing " + secrets)
            print("Maybe you forgot to copy it from -dist:")
            print("  cp test/secrets.py-dist test/secrets.py")
            sys.exit(1)

        pre_python26 = (sys.version_info[0] == 2
                        and sys.version_info[1] < 6)
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
        retcode = call(('pep8 %s/libcloud/ %s/test/' %
                (cwd, cwd)).split(' '))
        sys.exit(retcode)


class ApiDocsCommand(Command):
    description = "generate API documentation"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
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

# pre-2.6 will need the ssl PyPI package
pre_python26 = (sys.version_info[0] == 2 and sys.version_info[1] < 6)

setup(
    name='apache-libcloud',
    version=read_version_string(),
    description='A standard Python library that abstracts away differences' +
                'among multiple cloud provider APIs',
    author='Apache Software Foundation',
    author_email='dev@libcloud.apache.org',
    requires=([], ['ssl', 'simplejson'],)[pre_python26],
    packages=[
        'libcloud',
        'libcloud.utils',
        'libcloud.common',
        'libcloud.compute',
        'libcloud.compute.drivers',
        'libcloud.storage',
        'libcloud.storage.drivers',
        'libcloud.loadbalancer',
        'libcloud.loadbalancer.drivers',
        'libcloud.dns',
        'libcloud.dns.drivers'],
    package_dir={
        'libcloud': 'libcloud',
    },
    package_data={
        'libcloud': ['data/*.json']
    },
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
        'Programming Language :: Python :: 3.2'])
