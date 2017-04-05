Dimension Data Cloud Compute Driver Documentation
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
* ``dd-au-gov`` : Dimension Data Australia ACT (Canberra)
* ``dd-latam`` : Dimension Data Latin America
* ``dd-ap`` : Dimension Data Asia Pacific
* ``dd-canada`` : Dimension Data Canada region

The base `libcloud` API allows you to:

* list nodes, images, instance types, locations

Non-standard functionality and extension methods
------------------------------------------------

The Dimension Data driver exposes some `libcloud` non-standard
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

.. autoclass:: libcloud.compute.drivers.dimensiondata.DimensionDataNodeDriver
    :members:
    :inherited-members:

.. _`API`: http://cloud.dimensiondata.com/au/en/services/public-cloud/api


Debugging Tips
--------------

**Problem description: XML parsing issue for python version 2.7.5**

    *Example*::

      ip_address_collection=ip_addr_collection, child_ip_address_lists=None)
      File "/Users/andrewdas/Documents/Python/lib/python2.7/site-packages/libcloud/compute/drivers/dimensiondata.py", line 3185, in ex_edit_ip_address_list
        'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance"
      File "lxml.etree.pyx", line 2912, in lxml.etree.Element (src/lxml/lxml.etree.c:68681)
      File "apihelpers.pxi", line 140, in lxml.etree._makeElement (src/lxml/lxml.etree.c:15242)
      File "apihelpers.pxi", line 128, in lxml.etree._makeElement (src/lxml/lxml.etree.c:15125)
      File "apihelpers.pxi", line 287, in lxml.etree._initNodeAttributes (src/lxml/lxml.etree.c:17012)
      File "apihelpers.pxi", line 296, in lxml.etree._addAttributeToNode (src/lxml/lxml.etree.c:17180)
      File "apihelpers.pxi", line 1583, in lxml.etree._attributeValidOrRaise (src/lxml/lxml.etree.c:29377)
      ValueError: Invalid attribute name u'xmlns:xsi'

    *Solution*:
    - Upgrade to python version 2.7.12 and above