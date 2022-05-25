Google Storage Driver Documentation
===================================

Current version of the Google Storage driver in Libcloud uses S3 compatibility
layer and as such, only supports `XML API v1.0`_.

If you are a new Google Cloud Storage customers, you need to enable API v1.0
access and choose a default project in the Google Cloud Console for driver to
work.

For information on how to do that, please see the `official documentation`_.

If you don't do that, you will get a message that the request is missing a
project id header.

Known limitations
-----------------

1. Only lower case values are supported for metadata keys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Google Storage driver is implemented on top of the S3 compatible XML API. In
the XML API (and per AWS API docs), metadata values are sent as part of HTTP
request headers which means mixed casing is not supported for metadata keys (
all the metadata keys are lower cased).

Native Google Storage JSON API does  support mixed casing for metadata keys,
but that API is not supported by Libcloud.

To make migrating across different providers easier and for compatibility
reasons, you are encouraged to not rely on mixed casing for metadata header keys
even with the providers which support it.

2. Meta data / tags aren't returned when using list_container_objects method
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Meta data / tags associated with an object are only returned when using
:meth:`libcloud.storage.base.StorageDriver.get_object` method and not when
listing all the objects in a container using
:meth:`libcloud.storage.base.StorageDriver.list_container_objects` method.

This is a limitation of the Google Storage API v1.0.

API Docs
--------

.. autoclass:: libcloud.storage.drivers.google_storage.GoogleStorageDriver
    :members:
    :inherited-members:

.. _`XML API v1.0`: https://developers.google.com/storage/docs/reference-guide
.. _`official documentation`: https://developers.google.com/storage/docs/migrating#migration-simple
