Changes in Apache Libcloud v2.0
===============================

Replacement of httplib with `requests`
--------------------------------------

Apache Libcloud supports Python 2.6, 2.7 - 3.3 and beyond. To achieve this a package was written within the
Libcloud library to create a generic HTTP client for Python 2 and 3. This package has a custom implementation of a certificate store, searching and TLS preference configuration. One of the first errors to greet new users of Libcloud would be "No CA Certificates were found in CA_CERTS_PATH."... 

In 2.0 this implementation has been replaced with the `requests` package, and SSL verification should work against any publicly signed HTTPS endpoint by default, without having to provide a CA cert store.

Other changes include:

* Enabling HTTP redirects
* Allowing both global and driver-specific HTTP proxy configuration
* Consolidation of the LibcloudHTTPSConnection and LibcloudHTTPConnection into a single class, LibcloudConnection
* Support for streaming responses
* Support for mocking HTTP responses without having to mock the Connection class
* 10% typical performance improvement with the use of persistent TCP connections for each driver instance
* Access to the low-level TCP session is no longer available. Access to .read() on a raw connection will bind around `requests` body or iter_content methods.
* Temporary removal of the S3 very-large file support using the custom multi-part APIs. This will be added back in subsequent release candidates.

Allow redirects is enabled by default
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

HTTP redirects are allowed by default in 2.0. To disable redirects, set this global variable to False.

.. code-block:: Python

    import libcloud.http
    libcloud.http.ALLOW_REDIRECTS = False

HTTP/HTTPS Proxies
~~~~~~~~~~~~~~~~~~

Enabling a HTTP/HTTPS proxy is still supported and accessed via the driver's connection property or via the 'http_proxy' environment variable. Applying it to a driver will set the proxy for that driver only, using the environment
variable will make a global change.

.. code-block:: Python

  # option 1
  import os
  os.environ.get('http_proxy', 'http://localhost:8888/')

  # option 2
  driver.connection.connection.set_http_proxy(proxy_url='http://localhost:8888')


Adding support for Python 3.6 and deprecation of Python 3.2
-----------------------------------------------------------

In Apache Libcloud 2.0.0, Python 3.6 is `now supported <https://github.com/apache/libcloud/pull/965>`_ as a primary distribution.

Python 3.2 support has been dropped in this release and users should either upgrade to 3.3 or a newer version of Python.

SSL CA certificates are now bundled with the package
----------------------------------------------------

In Apache Libcloud 2.0.0, the `Mozilla Trusted Root Store <https://hg.mozilla.org/mozilla-central/raw-file/tip/security/nss/lib/ckfw/builtins/certdata.txt>`_ is bundled with the package, as part of the `requests` package bundle.
This means that users no longer have to set the path to a CA file either via installing the certifi package, downloading a PEM file or providing a directory in an environment variable.
All connections in Libcloud will assume HTTPS by default, now with 2.0.0, if those HTTPS endpoints have a signed certificate with a trusted CA authority, they will work with Libcloud by default.

Providing a custom client-side certificate, for example for a development server or a HTTPS proxy is still supported given providing a value to `libcloud.security.CA_CERTS_PATH`.

This code example would set a HTTP/HTTPS proxy and use a client-generated certificate to verify.

.. code-block:: Python

  import os
  os.environ.set('http_proxy', 'http://localhost:8888/')
  
  import libcloud.security
  libcloud.security.VERIFY_SSL_CERT = True
  libcloud.security.CA_CERTS_PATH = '/Users/anthonyshaw/charles.pem'


Providing a list of CA trusts is no longer supported
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In Apache Libcloud 2.0.0 if you provide a list of more than 1 path or certificate file in `libcloud.security.CA_CERTS_PATH` you will receive a warning and only the first path will be used. This path should be to a .cert or .pem file.
The environment variable REQUESTS_CA_BUNDLE can be used to access the requests library's list of trusted CAs.

Performance improvements and introduction of sessions
-----------------------------------------------------

Each instance of libcloud.common.base.Connection will have a LibcloudConnection instance under the `connection` property. In 1.5.0<, there would be 2 connection
class instances, LibcloudHttpConnection and LibcloudHttpsConnection, stored as an instance property `conn_classes`. In 2.0.0 this has been replaced with a single type,
:class:`libcloud.common.base.LibcloudHTTPConnection` that handles both HTTP and HTTPS connections. 

.. code-block:: Python

  def test():
      import libcloud
      import libcloud.compute.providers
      
      d = libcloud.get_driver(libcloud.DriverType.COMPUTE, libcloud.DriverType.COMPUTE.DIMENSIONDATA)
      instance = d('anthony', 'mypassword!', 'dd-au')
      instance.list_nodes() # is paged
      instance.list_images() # is paged
  
  if __name__ == '__main__':
      import timeit
      print(timeit.timeit("test()", setup="from __main__ import test", number=5))
      

This simple test shows a 10% performance improvement between Libcloud 1.5.0 and 2.0.0.

Changes to the storage API
--------------------------

Support for Buffered IO Streams
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The methods `upload_object_via_stream` now supports `file` objects, `BytesIO`, `StringIO` and generators as the iterator.

.. code-block:: Python

    with open('my_file_to_upload', 'rb') as iterator:
        obj = driver.upload_object_via_stream(iterator=iterator,
                                          container=containers[0],
                                          object_name='me.jpg',
                                          extra=extra)

Other minor changes
-------------------

- :class:`libcloud.common.base.Connection` will now use `urljoin` to combine the `request_path` and `method` URLs. This means that the URL action will always have a leading slash.

- The underlying connection classes do not assume HTTP if a non-standard port is used. They will use the preference set in the `secure` flag to the initializer of `Connection`.

- The storage download_object_as_stream method no longer buffers out file streams twice.
