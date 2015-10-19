HP Cloud Computer Driver Documentation
======================================

`HP Cloud`_ is a public cloud computing service offered by HP.

.. figure:: /_static/images/provider_logos/hpcloud.png
    :align: center
    :width: 300
    :target: https://www.hpcloud.com

HP Cloud driver is based on the OpenStack one. For more information
information and OpenStack specific documentation, please refer to
:doc:`OpenStack Compute Driver Documentation <openstack>` page.

Examples
--------

1. Instantiating the driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unlike other OpenStack based providers, HP cloud also requires you to specify
tenant name when connecting to their cloud. You can do that by passing
``tenant_name`` argument to the driver constructor as shown in the code example
below.

This attribute represents a project name and can be obtained in the `HP Cloud
console`_ as shown in the picture below.

.. figure:: /_static/images/misc/hp_cloud_console_projects.jpg
    :align: center
    :width: 800

.. literalinclude:: /examples/compute/openstack/hpcloud_native.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.compute.drivers.hpcloud.HPCloudNodeDriver
    :members:
    :inherited-members:

.. _`HP Cloud`: https://www.hpcloud.com
.. _`HP Cloud console`: https://horizon.hpcloud.com
