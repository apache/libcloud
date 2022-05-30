Getting Started
===============

Installation (stable version)
-----------------------------

Libcloud is available on PyPi. You can install latest stable version using pip:

.. sourcecode:: bash

    pip install apache-libcloud

Installation (development version)
----------------------------------

You can install latest development version from our Git repository:

.. sourcecode:: bash

    pip install -e git+https://git.apache.org/repos/asf/libcloud.git@trunk#egg=apache-libcloud

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

    import libcloud
    
    cls = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.RACKSPACE)


2. Instantiate the driver with your provider credentials

.. sourcecode:: python

   driver = cls('my username', 'my api key')

Keep in mind that some drivers take additional arguments such as ``region``
and ``api_version``.

For more information on which arguments you can pass to your provider driver,
see provider-specific documentation and the driver docstrings.

3. Start using the driver

.. sourcecode:: python

    pprint(driver.list_sizes())
    pprint(driver.list_nodes())

4. Putting it all together

.. sourcecode:: python

    from pprint import pprint

    import libcloud
    
    cls = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.RACKSPACE)
    
    driver = cls('my username', 'my api key')

    pprint(driver.list_sizes())
    pprint(driver.list_nodes())

You can find more examples with common patterns which can help you get started
on the :doc:`Compute Examples </compute/examples>` page.

Where to go from here?
----------------------

The best thing to do after understanding the basic driver work-flow is to visit
the documentation chapter for the API you are interested in (:doc:`Compute </compute/index>`, :doc:`Object Storage </storage/index>`,
:doc:`Load Balancer </loadbalancer/index>`, :doc:`DNS </dns/index>`). Chapter
for each API explains some basic terminology and things you need to know to
make an effective use of that API.

After you have a good grasp of those basic concepts, you are encouraged to
check the driver specific documentation (if available) and usage examples. If
the driver specific documentation for the provider you are interested in is
not available yet, you are encouraged to check docstrings for that driver.
