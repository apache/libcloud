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

API Docs
--------

.. autoclass:: libcloud.storage.drivers.google_storage.GoogleStorageDriver
    :members:
    :inherited-members:

.. _`XML API v1.0`: https://developers.google.com/storage/docs/reference/v1/apiversion1
.. _`official documentation`: https://developers.google.com/storage/docs/reference/v1/apiversion1#new
