Dimension Data Load Balancer Driver Documentation
=================================================

Dimension Data are a global IT Services company and form part of the NTT Group.
Dimension Data provide IT-as-a-Service to customers around the globe on their
cloud platform (Compute as a Service). The CaaS service is available either on
one of the public cloud instances or as a private instance on premises.

.. figure:: /_static/images/provider_logos/dimensiondata.png
    :align: center
    :width: 300
    :target: http://cloud.dimensiondata.com/

CaaS has its own non-standard `API`_ , `libcloud` provides a Python
wrapper on top of this `API`_ with common methods with other IaaS solutions and
Public cloud providers. Therefore, you can use use the Dimension Data libcloud
driver to communicate with both the public and private clouds.

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``user_id`` - Your Dimension Data Cloud username
* ``key`` - Your Dimension Data Cloud password
* ``region`` - The region key, one of the possible region keys

Possible regions:

* ``dd-na`` : Dimension Data North America (USA)
* ``dd-eu`` : Dimension Data Europe
* ``dd-af`` : Dimension Data Africa
* ``dd-au`` : Dimension Data Australia
* ``dd-latam`` : Dimension Data Latin America
* ``dd-ap`` : Dimension Data Asia Pacific
* ``dd-canada`` : Dimension Data Canada region

The base `libcloud` API allows you to:

* create balancers, add members and destroy members

Non-standard functionality and extension methods
------------------------------------------------

The Dimension Data driver exposes some `libcloud` non-standard
functionalities through extension methods and arguments.

These functionalities include:

* list nodes
* list pools
* set the network domain (zone)

For information on how to use these functionalities please see the method
docstrings below. You can also use an interactive shell for exploration as
shown in the examples.

API Docs
--------

.. autoclass:: libcloud.loadbalancer.drivers.dimensiondata.DimensionDataLBDriver
    :members:
    :inherited-members:

.. _`API`: http://cloud.dimensiondata.com/au/en/services/public-cloud/api
