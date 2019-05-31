Exoscale Computer Driver Documentation
======================================

`Exoscale`_ is a public European cloud provider with data centers in Germany,
Austria, and Switzerland.

.. figure:: /_static/images/provider_logos/exoscale.png
    :align: center
    :width: 300
    :target: https://www.exoscale.com

Exoscale driver is based on the CloudStack one and uses basic zones. For more
information and CloudStack specific documentation, please refer to
:doc:`CloudStack Compute Driver Documentation <cloudstack>` page.

Other Resources
---------------

* `Libcloud 0.14 and Exoscale`_ - Exoscale blog

API Docs
--------

.. autoclass:: libcloud.compute.drivers.exoscale.ExoscaleNodeDriver
    :members:
    :inherited-members:

.. _`Exoscale`: https://www.exoscale.ch
.. _`Libcloud 0.14 and Exoscale`: https://www.exoscale.ch/syslog/2014/01/27/licloud-guest-post/
