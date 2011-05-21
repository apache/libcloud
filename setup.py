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
from os.path import splitext, basename, join as pjoin

import libcloud.utils
libcloud.utils.SHOW_DEPRECATION_WARNING = False

HTML_VIEWSOURCE_BASE = 'https://svn.apache.org/viewvc/incubator/libcloud/trunk'
PROJECT_BASE_DIR = 'http://incubator.apache.org/libcloud/'
TEST_PATHS = [ 'test', 'test/compute', 'test/storage' , 'test/loadbalancer']
DOC_TEST_MODULES = [ 'libcloud.compute.drivers.dummy',
                     'libcloud.storage.drivers.dummy' ]

def read_version_string():
    version = None
    sys.path.insert(0, pjoin(os.getcwd()))
    from libcloud import __version__
    version = __version__
    sys.path.pop(0)
    return version

class TestCommand(Command):
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
        status = self._run_tests()
        sys.exit(status)

    def _run_tests(self):
        secrets = pjoin(self._dir, 'test', 'secrets.py')
        if not os.path.isfile(secrets):
            print "Missing %s" % (secrets)
            print "Maybe you forgot to copy it from -dist:"
            print "  cp test/secrets.py-dist test/secrets.py"
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
                print "Missing dependencies: %s" % ", ".join(missing)
                sys.exit(1)

        testfiles = []
        for test_path in TEST_PATHS:
            for t in glob(pjoin(self._dir, test_path, 'test_*.py')):
                testfiles.append('.'.join(
                    [test_path.replace('/', '.'), splitext(basename(t))[0]]))

        tests = TestLoader().loadTestsFromNames(testfiles)

        for test_module in DOC_TEST_MODULES:
            tests.addTests(doctest.DocTestSuite(test_module))

        t = TextTestRunner(verbosity = 2)
        res = t.run(tests)
        return not res.wasSuccessful()

class ApiDocsCommand(Command):
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
            % (HTML_VIEWSOURCE_BASE, PROJECT_BASE_DIR)
        )

class CoverageCommand(Command):
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
    description='A unified interface into many cloud server providers',
    author='Apache Software Foundation',
    author_email='libcloud@incubator.apache.org',
    requires=([], ['ssl', 'simplejson'],)[pre_python26],
    packages=[
        'libcloud',
        'libcloud.common',
        'libcloud.compute',
        'libcloud.compute.drivers',
        'libcloud.storage',
        'libcloud.storage.drivers',
        'libcloud.drivers',
        'libcloud.loadbalancer',
        'libcloud.loadbalancer.drivers',
    ],
    package_dir={
        'libcloud': 'libcloud',
    },
    package_data={
        'libcloud': ['data/*.json']
    },
    license='Apache License (2.0)',
    url='http://incubator.apache.org/libcloud/',
    cmdclass={
        'test': TestCommand,
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
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
