AuroraObjects Storage Driver Documentation
======================================

`PCextreme B.V.`_ is a Dutch cloud provider. It provides a public cloud offering
under the name AuroraCompute. All cloud services are under the family name Aurora.

All data is stored on servers in the European Union.

.. figure:: /_static/images/provider_logos/pcextreme.png
    :align: center
    :width: 300
    :target: https://www.pcextreme.nl/en/aurora/objects

Protocol
------------------

AuroraObjects talks the Amazon S3 protocol and thus supports almost all functions
which the Amazon S3 storage driver supports.

It however does not support CDN support. Calling any of the CDN functions will raise
a LibcloudError.

As a backend AuroraObjects uses `Ceph`_ for storage.

Multipart uploads
------------------

AuroraObjects storage driver supports multipart uploads which means you can
upload objects with a total size of up to 5 TB.

Multipart upload works similar to Amazon S3. After uploading all the parts the
AuroraObjects servers combine the parts into one large object.

If you use
:meth:`libcloud.storage.base.StorageDriver.upload_object_via_stream` method,
Libcloud transparently handles all the splitting and uploading of the parts
for you.

By default, to prevent excessive buffering and use of memory, each part is
5 MB in size. This is also the smallest size of a part you can use with the
multi part upload.

Examples
--------

Please refer to the Amazon S3 storage driver documentation for examples.


API Docs
--------

.. autoclass:: libcloud.compute.drivers.auroraobjects.AuroraObjectsStorageDriver
    :members:
    :inherited-members:

.. _`PCextreme B.V.`: https://www.pcextreme.nl/
.. _`Ceph`: https://ceph.com/
