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

Note that libcloud only supports general purpose storage accounts so make sure
to select the "Storage (general purpose v1)" account kind when creating your
storage account as shown on the screenshot below.

.. figure:: /_static/images/misc/azure_blobs_account_kind.png
    :align: center
    :width: 900

Instantiating a driver
~~~~~~~~~~~~~~~~~~~~~~

Once you have obtained your credentials you can instantiate the driver as shown
below.

.. literalinclude:: /examples/storage/azure/instantiate.py
   :language: python
