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
account and a Global API key available on the `account page`_ to the driver constructor
as shown below.

.. literalinclude:: /examples/dns/cloudflare/instantiate_driver.py
   :language: python

Alternatively, authentication can also be done via an API Token as shown below.
It is recommended that the token at least has the Zone.DNS permissions.

.. literalinclude:: /examples/dns/cloudflare/instantiate_driver_token.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.cloudflare.CloudFlareDNSDriver
    :members:
    :inherited-members:

.. _`CloudFlare`: https://www.cloudflare.com/
.. _`account page`: https://dash.cloudflare.com/profile
