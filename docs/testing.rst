:orphan:

Testing
=======

Prerequisites
-------------

.. note::

    If you use the tox method described below you don't need to install any
    dependencies, because tox automatically installs them for you in an virtual
    environment.

To run the libcloud test suite you need to have the following extra
dependencies installed:

* ``tox`` (``pip install tox``) - you only need this library if you want to
  use tox to run the tests with all the supported Python versions
* ``fasteners`` (``pip install fasteners``) - only used in the local storage
  driver
* ``coverage`` (``pip install coverage``) - you only need this library if you
  want to generate a test coverage report


Running Tests On All the Supported Python Versions Using tox
------------------------------------------------------------

.. note::
    tox uses virtualenv and won't pollute your local Python installation.

To run the tests on all the supported Python versions run the following command:

.. sourcecode:: bash

    tox

Running Tests Manually
----------------------

To run the tests manually, you first need to install all of the dependencies
mentioned above. After that simply go to the root of the repository and use the
following command:

.. sourcecode:: bash

    PYTHONPATH=. python setup.py test

Running a Single Test File
--------------------------

To run the tests located in a single test file, move to the root of the
repository and run the following command:

.. sourcecode:: bash

    PYTHONPATH=. python libcloud/test/<path to test file>

For example:

.. sourcecode:: bash

    PYTHONPATH=. python libcloud/test/compute/test_ec2.py

Generating Test Coverage Report
-------------------------------

To generate the test coverage run the following command:

.. sourcecode:: bash

    PYTHONPATH=. python setup.py coverage

When it completes you should see a new ``coverage_html_report`` directory which
contains the test coverage.

Running tests inside a Docker container
---------------------------------------

To run the tests on all the supported Python versions, run
the following command:

.. sourcecode:: bash

    contrib/run_tests.sh

This script creates a Docker container with all the supported Python versions
and runs tests inside the container using ``tox``.
