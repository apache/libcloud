Indosat Compute Driver Documentation
====================================

Indosat Cloud Infrastructure-as-a-Service ( IaaS ) from Indosat is the
enterprise-class IaaS services are designed and built using the infrastructure
hardware and software best and leading.
Cloud Indosat offered through an internet connection or through a closed
network of rental ( private leased line ).
Indosat Cloud Platform is built to support the automatic interaction and overall
arrangements , and supported by the server , storage and network elements
incorporated in virtualization technology application systems.

.. figure:: /_static/images/provider_logos/indosat.png
    :align: center
    :width: 300
    :target: http://www.indosatsingaporecloud.com/

IaaS has its own non-standard `API`_ , `libcloud` provides a Python
wrapper on top of this `API`_ with common methods with other IaaS solutions and
Public cloud providers. Therefore, you can use use the Indosat libcloud
driver to communicate with both the public and private clouds.

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``user_id`` - Your Indosat Cloud username
* ``key`` - Your Indosat Cloud password
* ``region`` - The region key, one of the possible region keys

Possible regions:

* ``indosat-id`` : Indosat Indonesia (ID) - **Default**
* ``indosat-na`` : Indosat North America (USA)
* ``indosat-eu`` : Indosat Europe
* ``indosat-af`` : Indosat Africa
* ``indosat-au`` : Indosat Australia

.. literalinclude:: /examples/compute/indosat/instantiate_driver.py
   :language: python

The base `libcloud` API allows you to:

* list nodes, images, instance types, locations

Non-standard functionality and extension methods
------------------------------------------------

The Indosat driver exposes some `libcloud` non-standard
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

.. autoclass:: libcloud.compute.drivers.indosat.IndosatNodeDriver
    :members:
    :inherited-members:

.. _`API`: http://www.indosatsingaporecloud.com/
