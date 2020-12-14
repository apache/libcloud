MinIO Storage Driver Documentation
==================================

`MinIO`_ is high performance, Kubernetes native object storage which exposes S3
compatible API.

.. figure:: /_static/images/provider_logos/minio.png
    :align: center
    :width: 300
    :target: https://min.io

Libcloud MinIO driver utilizes ``BaseS3StorageDriver`` class which utilizes S3
API.

Examples
--------

1. Connect to local MinIO installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example show how to connect to local MinIO installation which is running
using Docker containers (https://docs.min.io/docs/minio-docker-quickstart-guide.html).

.. literalinclude:: /examples/storage/minio/docker_example.py
   :language: python

.. _`MinIO`: https://min.io
