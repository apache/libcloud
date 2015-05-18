Cloudwatt Compute Driver Documentation
======================================

`Cloudwatt`_ is a public cloud provider based in Boulogne-Billancourt, France
with one datacenter at Val-de-Reuil

.. figure:: /_static/images/provider_logos/cloudwatt.png
    :align: center
    :width: 300
    :target: https://www.cloudwatt.com/fr/

Cloudwatt driver is based on the OpenStack driver so for more information about
that and OpenStack specific documentation, please refer to
:doc:`OpenStack Compute Driver Documentation <openstack>` page.

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``username`` - your Cloudwatt registered email
* ``password`` - your Cloudwatt password
* ``tenant_id`` - your Cloudwatt tenant ID
* ``tenant_name`` - your Cloudwatt tenant name

Tenant ID and name are foundable in the RC script available with web interface
at https://console.cloudwatt.com/overrides/access_and_security_overrides/view_credentials/

Examples
--------

Create instance
~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/cloudwatt/create_node.py

Create volume and attach
~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/cloudwatt/create_volume.py

API Docs
--------

.. autoclass:: libcloud.compute.drivers.cloudwatt.CloudwattNodeDriver
    :members:
    :inherited-members:

.. _`Cloudwatt`: https://www.cloudwatt.com/
