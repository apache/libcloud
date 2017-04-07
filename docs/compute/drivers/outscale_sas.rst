Outscale SAS Driver Documentation
=================================

`Outscale SAS`_ provides an IaaS platform allowing
developers to benefit from all the flexibility of the Cloud.
This IaaS platform relies on TINA OS, its Cloud manager whose purpose is to
provide great performances on the Cloud.
TINA OS is software developed by Outscale with APIs compatible with AWS EC2 (TM).

.. figure:: /_static/images/provider_logos/outscale.jpg
    :align: center
    :width: 300
    :target: https://www.outscale.com/

Outscale users can start virtual machines in the following regions:

* eu-west-1, France (Paris)
* eu-west-2, France (Paris)

For other Regions, see the `Outscale Inc.`_ documentation.

Outscale SAS is European company and is priced in Euros.

API Documentation
-----------------

.. autoclass:: libcloud.compute.drivers.ec2.OutscaleSASNodeDriver
    :members:
    :inherited-members:

.. _`Outscale SAS`: https://www.outscale.com/
.. _`Outscale Inc.`: outscale_inc.html
