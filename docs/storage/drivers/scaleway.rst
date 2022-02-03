Scaleway Storage Driver Documentation
==================================

Scaleway Object Storage is an Object Storage service based on the S3 protocol.

.. figure:: /_static/images/provider_logos/scaleway.svg
    :align: center
    :width: 300
    :target: https://www.scaleway.com/

Libcloud Scaleway Object Storage driver utilizes ``BaseS3StorageDriver`` class which utilizes S3
API.

Examples
--------

1. Upload a file to Scaleway's Object Storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example shows how to upload a local file to Scaleway's Object Storage.

Requirements: You have an account, credentials and have created an Object Storage Bucket (https://console.scaleway.com/object-storage/buckets).

.. literalinclude:: /examples/storage/scaleway/upload_example.py
   :language: python

.. _`Scaleway`: https://www.scaleway.com/
