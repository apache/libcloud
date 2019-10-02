Maxihost Compute Driver Documentation
=====================================

`Maxihost` is a cloud platform for bare metal servers.
.. figure:: /_static/images/provider_logos/maxihost.png

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following argument to the
driver constructor:

* ``api_key`` - Your API key. Can be obtained from https://control.maxihost.com/api

Example
-------

.. code-block:: python

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    cls = get_driver(Provider.MAXIHOST)

    driver = cls('api token')

API Docs
--------

.. _`Maxihost`: http://maxihost.com/
.. _`API`: https://developers.maxihost.com
