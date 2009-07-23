from distutils.core import setup
from distutils.core import Command
from unittest import TextTestRunner, TestLoader
from glob import glob
from os.path import splitext, basename, join as pjoin, walk
import os

class TestCommand(Command):
  user_options = [ ]

  def initialize_options(self):
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
    package_dir = {'libcloud' : 'src/libcloud', 'libcloud.drivers': 'src/libcloud/drivers' },
    license = 'BSD',
    url = 'http://github.com/cloudkick/libcloud',
    cmdclass = { 'test': TestCommand }
) 

