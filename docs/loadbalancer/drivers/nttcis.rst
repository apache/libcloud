NTTC-CIS Load Balancer Driver Documentation
=================================================

NTT Communications provide IT-as-a-Service to customers around the globe on their
cloud platform (Compute as a Service). The CaaS service is available either on
one of the public cloud instances or as a private instance on premises.

.. figure:: /_static/images/provider_logos/ntt.png
    :align: center
    :width: 300
    :target:  http://www.ntt.com/en/services/cloud/enterprise-cloud.html/

CaaS has its own non-standard `API`_, `libcloud` provides a Python
wrapper on top of this `API`_ with common methods with other IaaS solutions and
Public cloud providers. Therefore, you can use use the NTTC-CIS libcloud
driver to communicate with both the public and private clouds.

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``user_id`` - Your Dimension Data Cloud username
* ``key`` - Your Dimension Data Cloud password
* ``region`` - The region key, one of the possible region keys

Possible regions:

* ``na`` : NTTC-CIS North America (USA)
* ``eu`` : NTTC-CIS Europe
* ``af`` : NTTC-CIS Africa
* ``au`` : NTTC-CIS Australia
* ``ap`` : NTTC-CIS Asia Pacific
* ``ca`` : Dimension Data Canada region

The base `libcloud` API allows you to:

* create balancers, add members and destroy members

Non-standard functionality and extension methods
------------------------------------------------

The NTTC-CIS driver exposes some `libcloud` non-standard
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

.. autoclass:: libcloud.loadbalancer.drivers.nttcis.NttCisLBDriver
    :members:
    :inherited-members:

.. _`API`: https://docs.mcp-services.net/display/CCD/API+2