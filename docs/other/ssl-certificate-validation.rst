SSL Certificate Validation in <v2.0
===================================

When establishing a secure connection to a cloud provider endpoint,
Libcloud verifies server SSL certificate. By default, Libcloud searches
paths listed in ``libcloud.security.CA_CERTS_PATH`` variable for the CA
certificate files.

``CA_CERTS_PATH`` contains common paths to CA bundle installations on the
following platforms:

* ``certifi`` package on PyPi
* ``openssl`` package on CentOS / Fedora
* ``ca-certificates`` package on Debian / Ubuntu / Arch / Gentoo
* ``ca_root_nss`` port on FreeBSD
* ``curl-ca-bundle`` port on Mac OS X
* ``openssl`` and ``curl-ca-bundle`` homebrew package

If no valid CA certificate files are found, you will see an error message
similar to the one below:

``No CA Certificates were found in CA_CERTS_PATH.``

The easiest way to resolve this issue is to install `certifi` Python package
from PyPi using pip. This package provides curated collection of Root
Certificates based on the Mozilla CA bundle. If this package is installed
and available, Libcloud will use CA bundle which is bundled by default.

As the list of trusted CA certificates can and does change, you are also
encouraged to periodically update this package (``pip install --upgrade
certifi`` or similar).

If for some reason you want to avoid this behavior, you can set
``LIBCLOUD_SSL_USE_CERTIFI`` environment variable to ``false``. Or even,
better provide a direct path to the CA bundle you want to use using
``SSL_CERT_FILE`` environment variable as shown below.

Windows Users
-------------

The CA loading system does not load the Windows Certificate store, since this is not a directory.
Windows users should download the following file and place in a directory like %APPDATA%\libcloud or somewhere easily accessible.
https://raw.githubusercontent.com/bagder/ca-bundle/master/ca-bundle.crt

Then configure this file using one of the 2 methods in `Using a custom CA certificate`_

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
    libcloud.security.VERIFY_SSL_CERT = False

    # Instantiate and work with the driver here...
