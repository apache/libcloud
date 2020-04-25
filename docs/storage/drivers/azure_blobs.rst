Azure Blobs Storage Driver Documentation
========================================

Connecting to Azure Blobs
-------------------------

To connect to Azure Blobs you need your storage account name and access key.

You can retrieve this information in the Azure Management Portal by going to
"Storage Accounts" -> "Access Keys" as shown on the screenshots below.

.. figure:: /_static/images/misc/azure_blobs_manage_access_keys_1.png
    :align: center
    :width: 900


.. figure:: /_static/images/misc/azure_blobs_manage_access_keys_2.png
    :align: center
    :width: 900

The following types of storage accounts are supported in libcloud:

- `General-purpose v2 accounts`_
- `General-purpose v1 accounts`_
- `BlockBlobStorage accounts`_

Instantiating a driver
~~~~~~~~~~~~~~~~~~~~~~

Once you have obtained your credentials you can instantiate the driver as shown
below.

.. literalinclude:: /examples/storage/azure/instantiate.py
   :language: python

Connecting to self-hosted Azure Storage implementations
-------------------------------------------------------

To facilitate integration testing, libcloud supports connecting to the
`Azurite storage emulator`_. After starting the emulator, you can
instantiate the driver as shown below.

.. literalinclude:: /examples/storage/azure/instantiate_azurite.py
   :language: python

This instantiation strategy can also be adapted to connect to other self-hosted
Azure Storage implementations such as `Azure Blob Storage on IoT Edge`_.

.. _`General-purpose v2 accounts`: https://docs.microsoft.com/en-us/azure/storage/common/storage-account-overview#general-purpose-v2-accounts
.. _`General-purpose v1 accounts`: https://docs.microsoft.com/en-us/azure/storage/common/storage-account-overview#general-purpose-v1-accounts
.. _`BlockBlobStorage accounts`: https://docs.microsoft.com/en-us/azure/storage/common/storage-account-overview#blockblobstorage-accounts
.. _`Azurite storage emulator`: https://github.com/Azure/Azurite
.. _`Azure Blob Storage on IoT Edge`: https://docs.microsoft.com/en-us/azure/iot-edge/how-to-store-data-blob
