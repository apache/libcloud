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

from setuptools import setup
from distutils.core import Command
from unittest import TextTestRunner, TestLoader
from glob import glob
from os.path import splitext, basename, join as pjoin

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
PY2_pre_25 = PY2 and sys.version_info < (2, 5)
PY2_pre_26 = PY2 and sys.version_info < (2, 6)
PY2_pre_27 = PY2 and sys.version_info < (2, 7)
PY2_pre_279 = PY2 and sys.version_info < (2, 7, 9)
PY3_pre_32 = PY3 and sys.version_info < (3, 2)

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

SUPPORTED_VERSIONS = ['2.5', '2.6', '2.7', 'PyPy', '3.x']

TEST_REQUIREMENTS = [
    'mock'
]

if PY2_pre_279 or PY3_pre_32:
    TEST_REQUIREMENTS.append('backports.ssl_match_hostname')

if PY2_pre_27:
    unittest2_required = True
else:
    unittest2_required = False

if PY2_pre_25:
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


class TestCommand(Command):
    description = "run test suite"
    user_options = []
    unittest_TestLoader = TestLoader
    unittest_TextTestRunner = TextTestRunner

    def initialize_options(self):
        THIS_DIR = os.path.abspath(os.path.split(__file__)[0])
        sys.path.insert(0, THIS_DIR)
        for test_path in TEST_PATHS:
            sys.path.insert(0, pjoin(THIS_DIR, test_path))
        self._dir = os.getcwd()

    def finalize_options(self):
        pass

    def run(self):
        for module_name in TEST_REQUIREMENTS:
            try:
                __import__(module_name)
            except ImportError:
                print('Missing "%s" library. %s is library is needed '
                      'to run the tests. You can install it using pip: '
                      'pip install %s' % (module_name, module_name,
                                          module_name))
                sys.exit(1)

        if unittest2_required:
            try:
                from unittest2 import TextTestRunner, TestLoader
                self.unittest_TestLoader = TestLoader
                self.unittest_TextTestRunner = TextTestRunner
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

        if PY2_pre_26:
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

        # Test loader simply throws "'module' object has no attribute" error
        # if there is an issue with the test module so we manually try to
        # import each module so we get a better and more friendly error message
        for test_file in testfiles:
            try:
                __import__(test_file)
            except Exception:
                e = sys.exc_info()[1]
                print('Failed to import test module "%s": %s' % (test_file,
                                                                 str(e)))
                raise e

        tests = self.unittest_TestLoader().loadTestsFromNames(testfiles)

        for test_module in DOC_TEST_MODULES:
            tests.addTests(doctest.DocTestSuite(test_module))

        t = self.unittest_TextTestRunner(verbosity=2)
        res = t.run(tests)
        return not res.wasSuccessful()


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

install_requires = []
if PY2_pre_26:
    install_requires.extend(['ssl', 'simplejson'])

if PY2_pre_279 or PY3_pre_32:
    install_requires.append('backports.ssl_match_hostname')

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
    cmdclass={
        'test': TestCommand,
        'apidocs': ApiDocsCommand,
        'coverage': CoverageCommand
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
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy']
    )
