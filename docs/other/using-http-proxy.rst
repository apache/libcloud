Using an HTTP / HTTPS proxy
===========================

.. note::

    1. Support for HTTP proxies is available in Libcloud v0.16.0 and higher.
    2. Support for HTTPS proxies is available in Libcloud v2.5.1-dev and higher.
    3. In versions prior to v2.5.1-dev, ``driver.connection.set_http_proxy()``
       method is broken and you need to use
       ``driver.connection.connection.set_http_proxy()`` instead.

Libcloud supports using an HTTP / HTTPS proxy for outgoing HTTP and HTTPS
requests.

Proxy support has been tested with the following Python versions:

* Python 2.7 / PyPy
* Python 3.4
* Python 3.6
* Python 3.7

You can specify which HTTP(s) proxy to use using one of the approaches described
below:

* By setting ``http_proxy`` / ``https_proxy`` environment variable (this
  setting is system / process wide)
* By passing ``http_proxy`` argument to the
  :class:`libcloud.common.base.LibcloudConnection` class constructor (this
  setting is local to the connection instance)
* By calling :meth:`libcloud.common.base.LibcloudConnection.set_http_proxy`
  method aka ``driver.connection.connection.set_http_proxy`` (this setting
  is local to the connection instance)

Known limitations
-----------------

* Only HTTP basic access authentication proxy authorization method is supported
* If you are using HTTPS proxy you need to configure Libcloud to use CA cert
  bundle path which is used by the proxy server. See an example below on how to
  do that.

Examples
--------

This section includes some code examples which show how to use an HTTP(s) proxy
with Libcloud.

1. Using ``http_proxy`` / ``htps_proxy`` environment variable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By setting ``http_proxy`` / ``https_proxy`` environment variable you can
specify which proxy to use for all of the outgoing requests for a duration /
life-time of the process or a script.

Without authentication (http proxy):

.. sourcecode:: bash

    http_proxy=http://<proxy hostname>:<proxy port> python my_script.py

Without authentication (https proxy):

.. sourcecode:: bash

    http_proxy=https://<proxy hostname>:<proxy port> python my_script.py
    # or
    https_proxy=https://<proxy hostname>:<proxy port> python my_script.py


With basic auth authentication (http proxy):

.. sourcecode:: bash

    http_proxy=http://<username>:<password>@<proxy hostname>:<proxy port> python my_script.py

2. Passing ``proxy_url`` argument to the connection class constructor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

. note::

  Some drivers don't correctly pass ``proxy_url`` argument to the connection
  class and don't support ``proxy_url`` constructor argument.
  
  If you pass this argument to the driver constructor, but it doesn't appear
  to be working, it's likely the driver doesn't support this method.
  
  In such scenarios, you are advised to use some other method of setting a
  proxy (e.g. by setting an environment variable or by using
  :meth:`libcloud.common.base.LibcloudConnection.set_http_proxy` method).

By passing ``proxy_url`` argument to the
:class:`libcloud.common.base.Connection` class constructor, you can specify
which proxy to use for a particular connection.

.. literalinclude:: /examples/http_proxy/constructor_argument.py
   :language: python

3. Calling ``set_http_proxy`` method
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Calling ``set_http_proxy`` method allows you to specify which proxy to use
for all the outgoing requests which follow ``set_http_proxy`` method call.

This method also allows you to use a different proxy for each request as shown
in the example below.

.. literalinclude:: /examples/http_proxy/set_http_proxy_method.py
   :language: python

4. Using an HTTPS proxy
~~~~~~~~~~~~~~~~~~~~~~~

This example shows how to use an HTTPS proxy.

.. literalinclude:: /examples/http_proxy/https_proxy.py
   :language: python

To use an HTTPS proxy, you also need to configure Libcloud to use CA cert bundle
which is used by the HTTPS proxy server, to verify outgoing https request. If you
don't do that, you will see errors similar to the one below:

.. sourcecode:: python

    SSLError(1, u'[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed

Keep in mind that you will also receive a similar error message if you try to
use HTTP proxy for HTTPS requests.
