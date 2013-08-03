SSL Certificate Validation
==========================

When establishing a secure connection to a cloud provider endpoint,
Libcloud verifies server SSL certificate. By default, Libcloud searches
paths listed in ``libcloud.security.CA_CERTS_PATH`` for CA certificate files.

``CA_CERTS_PATH`` contains common paths to CA bundle installations on the
following platforms:

* openssl on CentOS / Fedora
* ca-certificates on Debian / Ubuntu / Arch / Gentoo
* ca_root_nss on FreeBSD
* curl-ca-bundle on Mac OS X

If no valid CA certificate files are found, you will see an error message
similar to the one bellow:

``No CA Certificates were found in CA_CERTS_PATH.``

Acquiring CA Certificates
-------------------------

If the above packages are unavailable to you, and you don't wish to roll
your own, the makers of cURL provides an excellent resource, generated
from Mozilla: http://curl.haxx.se/docs/caextract.html.
