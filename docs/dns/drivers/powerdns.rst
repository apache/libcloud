PowerDNS Driver Documentation
=============================

`PowerDNS`_ is an open-source DNS server.

The current libcloud PowerDNS driver uses the HTTP API from PowerDNS 3.x by
default. Please read the `PowerDNS 3 HTTP API documentation`_ to enable the
HTTP API on your PowerDNS server. Specifically, you will need to set the
following in ``pdns.conf``::

  experimental-json-interface=yes
  experimental-api-key=changeme
  webserver=yes

For PowerDNS 4.x, please read the `PowerDNS 4 HTTP API documentation`_. The
``pdns.conf`` options are slightly different (the options are no longer
prefixed with ``experimental-``, and ``json-interface`` is no longer
required.)::

  api-key=changeme
  webserver=yes

Be sure to reload the pdns service after any configuration changes.

Instantiating the driver
------------------------

To instantiate the driver you need to pass the API key, hostname, and webserver
HTTP port to the driver constructor as shown below.

.. literalinclude:: /examples/dns/powerdns/instantiate_driver.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.powerdns.PowerDNSDriver
    :members:
    :inherited-members:

.. _`PowerDNS`: https://doc.powerdns.com/
.. _`PowerDNS 3 HTTP API documentation`: https://doc.powerdns.com/3/httpapi/README/
.. _`PowerDNS 4 HTTP API documentation`: https://doc.powerdns.com/authoritative/http-api/
