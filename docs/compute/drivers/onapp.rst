OnApp Compute Driver Documentation
==================================

`OnApp`_ software enables Infrastructure-as-a-Service for hosts, telcos and
other service providers. It's a turnkey platform for selling cloud, VPS,
dedicated servers, CDN and more through a "single pane of glass" control panel,
and now supports Xen, KVM, VMware and Amazon EC2.

.. figure:: /_static/images/provider_logos/onapp.png
    :align: center
    :width: 382
    :target: http://onapp.com/

`OnApp`_ has its own non-standard `API`_ , `libcloud` provides a Python
wrapper on top of this `API`_ with common methods with other IaaS solutions and
Public cloud providers. Therefore, you can use the `OnApp` libcloud
driver to communicate with OnApp public clouds.

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``key`` - Your OnApp username
* ``secret`` - Your OnApp password
* ``host`` - The host of your OnApp endpoint
* ``path`` - The path to your OnApp endpoint
  (e.g ``/client/api`` for ``http://onapp.test/client/api``)
* ``url`` - The url to your OnApp endpoint, mutually exclusive with
  ``host`` and ``path``
* ``secure`` - True or False. True by default

To authenticate using API key, put your account email as ``key`` and the API key
to the server as ``secret``.

Example
-------

.. literalinclude:: /examples/compute/onapp/functionality.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.compute.drivers.onapp.OnAppNodeDriver
    :members:
    :inherited-members:

.. _`OnApp`: http://onapp.com/
.. _`API`: https://docs.onapp.com/display/31API/OnApp+3.1+API+Guide
