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

VPS (Virtual Private Server) support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The OVH driver also supports managing OVH VPS instances, which are a separate
product line from the Public Cloud. VPS methods use the ``/vps/`` API and are
available as ``ex_``-prefixed extension methods.

Note: VPS operations do not require ``ex_project_id``, but the driver
constructor still requires it for Public Cloud operations. You can pass any
value if you only need VPS functionality.

.. code-block:: python

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    Ovh = get_driver(Provider.OVH)
    driver = Ovh(
        "your_app_key",
        "your_app_secret",
        "project_id",
        "your_consumer_key",
    )

    # List all VPS
    vps_names = driver.ex_list_vps()
    for name in vps_names:
        node = driver.ex_get_vps(name)
        print(f"{node.name}: {node.state} - IPs: {node.public_ips}")

    # Reboot a VPS
    driver.ex_reboot_vps("vps-12345678.vps.ovh.net")

    # List available OS images for a VPS
    images = driver.ex_list_vps_images("vps-12345678.vps.ovh.net")
    for image in images:
        print(f"{image.id}: {image.name}")

    # Rebuild a VPS with a new OS
    driver.ex_rebuild_vps(
        "vps-12345678.vps.ovh.net",
        "img-debian-12",
        ssh_key=["ssh-rsa AAAA..."],
    )

API Docs
--------

.. autoclass:: libcloud.compute.drivers.ovh.OvhNodeDriver
    :members:
    :inherited-members:

.. _`OVH`: https://www.ovh.com
.. _`API console`: https://api.ovh.com/console/#/
