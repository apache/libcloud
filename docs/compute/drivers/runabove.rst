RunAbove Compute Driver Documentation
=====================================

`RunAbove`_ is a public cloud offer created by OVH Group with datacenters
in North America and Europe.

.. figure:: /_static/images/provider_logos/runabove.png
    :align: center
    :width: 300
    :target: https://www.runabove.com/index.xml

RunAbove driver uses the OVH/RunAbove API so for more information about
that, please refer to `RunAbove knowledge base`_ page and `API console`_.

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``key`` - Application key
* ``secret`` - Application secret
* ``ex_consumer_key`` - Consumer key

For get application key and secret, you must first register an application
at https://api.runabove.com/createApp/. Next step, create a consumer key with
following command: ::

    curl -X POST \
        -H 'X-Ra-Application: youApplicationKey' \
        -H 'Content-Type: application/json' \
        -d '{
            "accessRules":
                [
                    {"method":"GET","path":"/*"},
                    {"method":"POST","path":"/*"},
                    {"method":"DELETE","path":"/*"},
                    {"method":"PUT","path":"/*"},
                ],
                "redirection":"http://runabove.com"
            }' \
        "https://api.runabove.com/1.0/auth/credential"

This will answer a JSON like below with inside your Consumer Key and
``validationUrl``. Follow this link for valid your key. ::

    {
      "validationUrl":"https://api.runabove.com/login/?credentialToken=fIDK6KCVHfEMuSTP3LV84D3CsHTq4T3BhOrmEEdd2hQ0CNcfVgGVWZRqIlolDJ3W",
      "consumerKey":"y7epYeHCIqoO17BzBgxluvB4XLedpba9",
      "state":"pendingValidation"
    }

Now you have and can use you credentials with Libcloud.

Examples
--------

Create node
~~~~~~~~~~~

.. literalinclude:: /examples/compute/runabove/create_node.py

Create and attach a volume to a node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/runabove/attach_volume.py

API Docs
--------

.. autoclass:: libcloud.compute.drivers.runabove.RunAboveNodeDriver
    :members:
    :inherited-members:

.. _`Runabove`: https://www.runabove.com/index.xml
.. _`RunAbove knowledge base`: https://community.runabove.com/kb/
.. _`API console`: https://api.runabove.com/console/#/
