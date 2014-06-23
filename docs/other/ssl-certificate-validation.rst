SSL Certificate Validation
==========================

When establishing a secure connection to a cloud provider endpoint,
Libcloud verifies server SSL certificate. By default, Libcloud searches
paths listed in ``libcloud.security.CA_CERTS_PATH`` variable for the CA
certificate files.

``CA_CERTS_PATH`` contains common paths to CA bundle installations on the
following platforms:

* ``openssl`` package on CentOS / Fedora
* ``ca-certificates`` package on Debian / Ubuntu / Arch / Gentoo
* ``ca_root_nss`` port on FreeBSD
* ``curl-ca-bundle`` port on Mac OS X

If no valid CA certificate files are found, you will see an error message
similar to the one bellow:

``No CA Certificates were found in CA_CERTS_PATH.``

Acquiring CA Certificates
-------------------------

If the above packages are unavailable to you, and you don't wish to roll
your own, the makers of cURL provides an excellent resource, generated
from Mozilla: http://curl.haxx.se/docs/caextract.html.

Using a custom CA certificate
-----------------------------

If you want to use a custom CA certificate file for validating the server
certificate, you can do that using two different approaches:

1. Setting ``SSL_CERT_FILE`` environment variable to point to your CA file

.. sourcecode:: bash

    SSL_CERT_FILE=/home/user/path-to-your-ca-file.crt python my_script.py

2. Setting ``libcloud.security.CA_CERTS_PATH`` variable in your script to 
   point to your CA file

.. sourcecode:: python

    import libcloud.security
    libcloud.security.CA_CERTS_PATH = ['/home/user/path-to-your-ca-file.crt']

    # Instantiate and work with the driver here...

Adding additional CA certificate to the path
--------------------------------------------

If you want to add an additional CA certificate to the ``CA_CERTS_PATH``, you
can do this by appending a path to your CA file to the
``libcloud.security.CA_CERTS_PATH`` list.

For example:

.. sourcecode:: python

    import libcloud.security
    libcloud.security.CA_CERTS_PATH.append('/home/user/path-to-your-ca-file.crt')

    # Instantiate and work with the driver here...

Disabling SSL certificate validation
------------------------------------

.. note::

    Disabling SSL certificate validations makes you vulnerable to MITM attacks
    so you are strongly discouraged from doing that. You should only disable it
    if you are aware of the consequences and you know what you are doing.

To disable SSL certificate validation, set
``libcloud.security.VERIFY_SSL_CERT`` variable to ``False`` at the top of your
script, before instantiating a driver and interacting with other Libcloud code.

For example:

.. sourcecode:: python

    import libcloud.security
    libcloud.security.VERIFY_SSL_CERT = True

    # Instantiate and work with the driver here...
