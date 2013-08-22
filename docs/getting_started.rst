Getting Started
===============

Installation (stable version)
-----------------------------

Libcloud is available on PyPi. You can install latest stable version using pip:

.. sourcecode:: bash

    pip install apache-libcloud

Installation (development version)
----------------------------------

You can install latest development version from out Git repository:

.. sourcecode:: bash

    pip install -e https://git-wip-us.apache.org/repos/asf/libcloud.git@trunk#egg=apache-libcloud

Upgrading
---------

If you used pip to install the library you can also use it to upgrade it:

.. sourcecode:: bash

    pip install --upgrade apache-libcloud

Using it
--------

This section describes a standard work-flow which you follow when working
with any of the Libcloud drivers.

1. Obtain reference to the provider driver

.. sourcecode:: python

    from pprint import pprint

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    cls = get_driver(Provider.RACKSPACE)

2. Instantiate the driver with your provider credentials

.. sourcecode:: python

   driver = cls('my username', 'my api key')

3. Start using the driver

.. sourcecode:: python

    pprint(driver.list_sizes())
    pprint(driver.list_nodes())

4. Putting it all together

.. sourcecode:: python

    from pprint import pprint

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    cls = get_driver(Provider.RACKSPACE)
    driver = cls('my username', 'my api key')

    pprint(driver.list_sizes())
    pprint(driver.list_nodes())

You can find more examples with common patterns which can help you get started
on the :doc:`Compute Examples </compute/examples>` page.

Where to go from here?
----------------------
