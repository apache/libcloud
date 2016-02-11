NTT America Public Cloud Compute Driver Documentation
=====================================================

The NTT America Cloud delivers enterprise-class infrastructure that allows customers
to scale to meet demand in real time, and then shut down those resources when they
are no longer needed. The deployment of private networks, each with their own
customizable firewall, enables test and development environments to be logically
separated, but still in the same VMware environment in which the applications will run.

Private networks, firewalls, load balancing and servers are deployed in
minutes through the easy-to-use web-based control panel, or through standards based APIs.
The support of burstable CPU means that capacity is always available when needed.
The flexible payment and reporting options mean customers can get detailed reports on
activity across their organization, allocate costs where appropriate, and receive
valuable information for management and budgeting purposes.


.. figure:: /_static/images/provider_logos/ntta.png
    :align: center
    :width: 300
    :target: http://www.us.ntt.com/

CaaS has its own non-standard `API`_ , `libcloud` provides a Python
wrapper on top of this `API`_ with common methods with other IaaS solutions and
Public cloud providers. Therefore, you can use use the NTT America libcloud
driver to communicate with both the public and private clouds.

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``user_id`` - Your NTT America Cloud username
* ``key`` - Your NTT America Cloud password
* ``region`` - The region key, one of the possible region keys

Possible regions:

* ``ntta-na`` : NTT America North America (USA) - **Default**
* ``ntta-eu`` : NTT America Europe
* ``ntta-af`` : NTT America Africa
* ``ntta-au`` : NTT America Australia
* ``ntta-ap`` : NTT America Asia Pacific

.. literalinclude:: /examples/compute/ntta/instantiate_driver.py
   :language: python

The base `libcloud` API allows you to:

* list nodes, images, instance types, locations

Non-standard functionality and extension methods
------------------------------------------------

The NTT America driver exposes some `libcloud` non-standard
functionalities through extension methods and arguments.

These functionalities include:

* start and stop a node
* list networks
* create firewalls, configure network address translation
* provision layer 3 networks

For information on how to use these functionalities please see the method
docstrings below. You can also use an interactive shell for exploration as
shown in the examples.

API Docs
--------

.. autoclass:: libcloud.compute.drivers.ntta.NTTAmericaNodeDriver
    :members:
    :inherited-members:

.. _`API`: http://www.us.ntt.com/en/services/cloud/public-cloud.html
