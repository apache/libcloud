CloudFlare DNS Driver Documentation
===================================

`CloudFlare`_, Inc. is a U.S. company that provides a content delivery network
and distributed domain name server services.

.. figure:: /_static/images/provider_logos/cloudflare.png
    :align: center
    :width: 300
    :target: https://www.cloudflare.com

Instantiating the driver
------------------------

To instantiate the driver you need to pass email address associated with your
account and API key available on the `account page`_ to the driver constructor
as shown below.

.. literalinclude:: /examples/dns/cloudflare/instantiate_driver.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.cloudflare.CloudFlareDNSDriver
    :members:
    :inherited-members:

.. _`CloudFlare`: https://www.cloudflare.com/
.. _`account page`: https://www.cloudflare.com/my-account.html
