GoDaddy DNS Driver Documentation
================================

`GoDaddy`_ provide domain name registration and are the worlds largest with over 13 million customers. They also provide nameservers and DNS hosting as
well as cloud and website hosting.

.. figure:: /_static/images/provider_logos/godaddy.png
    :align: center
    :width: 300
    :target: https://www.godaddy.com/

Further information on `GoDaddy`_ API is available on the `GoDaddy API Website`_

Driver features
---------------

* Manage the records for GoDaddy hosted domains
* Price and purchase domains with an existing GoDaddy account
* Fetch legal agreements required to register and purchase domains for a range of TLDs
* Submit completed agreements to purchase domains

Instantiating the driver
------------------------

Before you instantiate a driver, you will need a GoDaddy account.

Once you have an account you need to request a Production key on the GoDaddy API website: 
https://developer.godaddy.com/getstarted#access 

You can then use these details to instantiate a driver with the arguments:

* `shopper_id` - Your customer ID
* `key` - An API key
* `secret` - The matching secret for the API key

.. literalinclude:: /examples/dns/godaddy/instantiate_driver.py
   :language: python

Listing zones
-------------

.. literalinclude:: /examples/dns/godaddy/listing_zones.py
   :language: python

Returns

::

    Zone : wassle-layer.com
    Expires: 2018-09-30T18:22:00Z
    Zone : wizzle-wobble.org
    Expires: 2017-01-04T04:02:07Z

Listing records
---------------

.. literalinclude:: /examples/dns/godaddy/listing_records.py
   :language: python

Returns

::

    Type : CNAME
    Data: @
    TTL: 3600
    Type : CNAME
    Data: @
    TTL: 3600
    Type : MX
    Data: mailstore1.secureserver.net
    TTL: 3600
    Type : MX
    Data: smtp.secureserver.net
    TTL: 3600

Adding records
--------------

.. literalinclude:: /examples/dns/godaddy/adding_records.py
   :language: python

Updating records
----------------

.. literalinclude:: /examples/dns/godaddy/updating_records.py
   :language: python

It is important to note that the GoDaddy API does not give records a unique identifier.
So if you have multiple existing records for a single data and type, e.g. 2 A records for www, they will both be replaced with 1 record if you run the update_records method

Pricing a domain
----------------

The driver supports checking the availability of a domain that you would like to purchase.

.. literalinclude:: /examples/dns/godaddy/pricing_domain.py
   :language: python

Purchasing a domain
-------------------

Domains can be purchased by requesting the agreement schema, which is a JSON schema and submitted a completed document.

.. literalinclude:: /examples/dns/godaddy/purchasing_domain.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.godaddy.GoDaddyDNSDriver
    :members:
    :inherited-members:

.. _`GoDaddy`: https://godaddy.com/
.. _`GoDaddy API Website`: https://developer.godaddy.com/doc
