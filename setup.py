from distutils.core import setup
from distutils.core import Command
from unittest import TextTestRunner, TestLoader
from glob import glob
from os.path import splitext, basename, join as pjoin
import os
import sys

sys.path.insert(0, 'py/')

class TestCommand(Command):
  user_options = [ ]

  def initialize_options(self):
    THIS_DIR = os.path.abspath(os.path.split(__file__)[0])
    sys.path.insert(0, THIS_DIR)
    sys.path.insert(0, pjoin(THIS_DIR, 'test'))
    self._dir = os.getcwd()

  def finalize_options(self):
    pass

  def run(self):
    testfiles = [ ]
    for t in glob(pjoin(self._dir, 'test', 'test_*.py')):
      if not t.endswith('__init__.py'):
        testfiles.append('.'.join(
          ['test', splitext(basename(t))[0]])
        )

    tests = TestLoader().loadTestsFromNames(testfiles)
    t = TextTestRunner(verbosity = 1)
    t.run(tests)

setup(name = 'libcloud',
    version = '0.1.0',
    description = 'A unified interface into many cloud server providers',
    author = 'Alex Polvi',
    author_email = 'polvi@cloudkick.com',
    packages = ['libcloud', 'libcloud.drivers'],
    package_dir = {'libcloud' : 'libcloud', 'libcloud.drivers': 'libcloud/drivers' },
    license = 'Apache License (2.0)',
    url = 'http://github.com/cloudkick/libcloud',
    cmdclass = { 'test': TestCommand }
) 

