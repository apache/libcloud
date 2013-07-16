CloudFrames Compute Driver Documentation
========================================

Connecting to the CloudFrames installation
----------------------------------------

This will tell you how to interpret the available arguments:

* ``key`` - The username to the cloudapi
* ``secret`` - The password to the cloudapi
* ``secure`` - This should always be False as the cloudapi doesn't support ssl
* ``host`` - The hostname or ip address we can reach the cloudapi on
* ``port`` - The port the cloudapi runs on (defaults to 80 for http)
* ``url`` - As an alternative to the above, you can pass the full cloudapi url
  (e.g. ``http://admin:admin@cloudframes:80/appserver/xmlrpc``)

Examples
--------

1. Creating the connection
~~~~~~~~~~~~~~~~~~~~~~~~~~

You can set up the connection using either the complete url to the api.

.. literalinclude:: /examples/compute/cloudframes/auth_url.py

Or by specifying the individual components which would make up the url.

.. literalinclude:: /examples/compute/cloudframes/auth_kwargs.py

2. Implemented functionality
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. literalinclude:: /examples/compute/cloudframes/functionality.py
