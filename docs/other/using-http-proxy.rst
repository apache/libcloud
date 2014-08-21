Using an HTTP proxy
===================

.. note::

    Support for HTTP proxies is only available in Libcloud trunk and higher.

Libcloud supports using an HTTP proxy for outgoing HTTP and HTTPS requests. 

Proxy support has been tested with the following Python versions;

* Python 2.6
* Python 2.7 / PyPy
* Python 3.1
* Python 3.2
* Python 3.3
* Python 3.4

You can specify which HTTP proxy to use using one of the approaches described
bellow:

* By setting ``http_proxy`` environment variable (this setting is system /
  process wide)
* By passing ``http_proxy`` argument to the
  :class:`libcloud.common.base.LibcloudHTTPConnection` class constructor (this
  setting is local to the connection instance)
* By calling :meth:`libcloud.common.base.LibcloudHTTPConnection.set_http_proxy`
  method (this setting is local to the connection instance)

Known limitations
-----------------

* Only HTTP basic access authentication proxy authorization method is supported

Examples
--------

This section includes some code examples which show how to use an HTTP proxy
with Libcloud.

1. Using ``http_proxy`` environment variable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By setting ``http_proxy`` environment variable you can specify which proxy to
use for all of the outgoing requests for a duration / life-time of the process
or a script.

Without authentication:

.. sourcecode:: python

    http_proxy=http://<proxy hostname>:<proxy port> python my_script.py

With basic auth authentication:

.. sourcecode:: python

    http_proxy=http://<username>:<password>@<proxy hostname>:<proxy port> python my_script.py

2. Passing ``http_proxy`` argument to the connection class constructor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By passing ``http_proxy`` argument to the
:class:`libcloud.common.base.Connection` class constructor, you can specify
which proxy to use for a particular connection.

.. literalinclude:: /examples/http_proxy/constructor_argument.py
   :language: python

3. Calling ``set_http_proxy`` method
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Calling ``set_http_proxy`` method allows you to specify which proxy to use
for all the outgoing requests which follow ``set_http_proxy`` method call.

This method also allows you to use a different proxy for each request as shown
in the example bellow.

.. literalinclude:: /examples/http_proxy/set_http_proxy_method.py
   :language: python
