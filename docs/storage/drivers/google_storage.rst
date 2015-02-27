Google Storage Storage Driver Documentation
===========================================

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

1. Meta data / tags aren't returned when using list_container_objects method
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
