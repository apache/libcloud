Google DNS Driver Documentation
===================================

Google Cloud DNS is a scalable, reliable and managed authoritative
Domain Name System (DNS) service running on the same infrastructure as Google.

.. figure:: /_static/images/provider_logos/gcp.png
    :align: center
    :width: 500
    :target: https://cloud.google.com/

Instantiating the driver
------------------------

The Google Cloud DNS driver supports three methods of authentication:
* Service accounts
* Installed Application
* Internal authentication

To instantiate the driver, pass authentication tokens to the constructor as
shown below:

1. Getting Driver with Service Account authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With local key file:

.. literalinclude:: /examples/dns/google/dns_service_account.py

With Service Account credentials as dict:

.. literalinclude:: /examples/dns/google/dns_service_account_infile.py

2. Getting Driver with Installed Application authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/dns/google/dns_installed_application.py


3. Using GCE Internal Authorization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/dns/google/dns_internal_auth.py


API Docs
--------

.. autoclass:: libcloud.dns.drivers.google.GoogleDNSDriver
    :members:
    :inherited-members:
