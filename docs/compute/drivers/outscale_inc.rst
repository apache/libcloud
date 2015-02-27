Outscale INC Driver Documentation
=================================

`Outscale INC`_ provides an IaaS platform allowing
developers to benefit from all the flexibility of the Cloud.
This IaaS platform relies on TINA OS, its Cloud manager which purpose is to
provide great performances on the Cloud.
TINA OS is an own developed software with APIs compatible with AWS EC2 (TM).

.. figure:: /_static/images/provider_logos/outscale.png
    :align: center
    :width: 300
    :target: https://www.outscale.com/

Outscale users can start virtual machines in the following regions:

* EU West (Paris France) Region
* US East (Boston US) Region
* (Soon) US East (New Jersey) Region
* (Soon) Asia (Hong Kong) Region

Outscale INC is an American company: prices are in $.

API Docs
--------

.. autoclass:: libcloud.compute.drivers.ec2.OutscaleINCNodeDriver
    :members:
    :inherited-members:

.. _`Outscale INC`: https://www.outscale.com/
