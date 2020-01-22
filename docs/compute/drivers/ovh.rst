OVH Compute Driver Documentation
================================

`OVH`_ is an Internet Service Provider providing dedicated servers, shared and
cloud hosting, domain registration, and VOIP telephony services.

.. figure:: /_static/images/provider_logos/ovh.png
    :align: center
    :width: 300
    :target: https://www.ovh.com

OVH driver uses a REST API, for more information about that, please refer to
`API console`_.

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``key`` - Application key
* ``secret`` - Application secret
* ``ex_project_id`` - Project ID
* ``ex_consumer_key`` - Consumer key

For get application key and secret, you must register an application
at https://eu.api.ovh.com/createApp/. Next step, create a consumer key with
following command: ::

    curl -X POST \
        -H 'X-Ovh-Application: youApplicationKey' \
        -H 'Content-Type: application/json' \
        -d '{
            "accessRules":
                [
                    {"method":"GET","path":"/*"},
                    {"method":"POST","path":"/*"},
                    {"method":"DELETE","path":"/*"},
                    {"method":"PUT","path":"/*"}
                ],
                "redirection":"http://ovh.com"
            }' \
        https://eu.api.ovh.com/1.0/auth/credential

This will answer a JSON like below with inside your Consumer Key and
``validationUrl``. Follow this link for valid your key. ::

    {
      "validationUrl":"https://eu.api.ovh.com/auth/?credentialToken=fIDK6KCVHfEMuSTP3LV84D3CsHTq4T3BhOrmEEdd2hQ0CNcfVgGVWZRqIlolDJ3W",
      "consumerKey":"y7epYeHCIqoO17BzBgxluvB4XLedpba9",
      "state":"pendingValidation"
    }


Secondly, you must create a cloud project and retrieve its ID, from URL for
example.

Now you have and can use you credentials with Libcloud.

Examples
--------

Create node
~~~~~~~~~~~

.. literalinclude:: /examples/compute/ovh/create_node.py

Create and attach a volume to a node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/ovh/attach_volume.py

API Docs
--------

.. autoclass:: libcloud.compute.drivers.ovh.OvhNodeDriver
    :members:
    :inherited-members:

.. _`OVH`: https://www.ovh.com
.. _`API console`: https://api.ovh.com/console/#/
