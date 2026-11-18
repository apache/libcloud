AuroraObjects Storage Driver Documentation
==========================================

`PCextreme B.V.`_ is a Dutch cloud provider. It provides a public cloud offering
under the name AuroraCompute. All cloud services are under the family name Aurora.

All data is stored on servers in the European Union.

.. figure:: /_static/images/provider_logos/pcextreme.png
    :align: center
    :width: 300
    :target: https://www.pcextreme.com/aurora/objects

Protocol
--------

AuroraObjects talks the Amazon S3 protocol and thus supports almost all functions
which the Amazon S3 storage driver supports.

It however does not support CDN support. Calling any of the CDN functions will raise
a LibcloudError.

As a backend AuroraObjects uses `Ceph`_ for storage.

Instantiating a driver
----------------------

When instantiating the AuroraObjects you need a access key and secret key.
These can be obtained from the `Control Panel`_ of AuroraObjects.

With these credentials you can instantiate the driver:

.. literalinclude:: /examples/storage/auroraobjects/instantiate.py
   :language: python

Multipart uploads
-----------------

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

.. autoclass:: libcloud.storage.drivers.auroraobjects.AuroraObjectsStorageDriver
    :members:
    :inherited-members:

.. _`PCextreme B.V.`: https://www.pcextreme.com/
.. _`Ceph`: https://ceph.com/
.. _`Control Panel`: https://cp.pcextreme.nl/
