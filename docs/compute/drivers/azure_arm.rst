Azure ARM Compute Driver Documentation
======================================

Azure driver allows you to integrate with Microsoft `Azure Virtual Machines`_
provider using the `Azure Resource Management`_ (ARM) API.

.. figure:: /_static/images/provider_logos/azure.jpg
    :align: center
    :width: 300
    :target: http://azure.microsoft.com/en-us/services/virtual-machines/

Azure Virtual Machine service allows you to launch Windows and Linux virtual
servers in many datacenters across the world.

Connecting to Azure
-------------------

To connect to Azure you need your tenant ID and subscription ID.  Using the
Azure cross platform CLI, use ``az account list`` to get these
values.

Creating a Service Principal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following directions are based on
https://azure.microsoft.com/en-us/documentation/articles/resource-group-authenticate-service-principal/

.. sourcecode:: bash

  az ad app create --display-name "<Your Application Display Name>" --identifier-uris "<https://YouApplicationUri>" --password <Your_Password>
  az ad sp create --id "<Application_Id>"
  az role assignment create --assignee "<Object_Id>" --role Owner --scope /subscriptions/{subscriptionId}/

Instantiating a driver
~~~~~~~~~~~~~~~~~~~~~~

Use <Application_Id> for "key" and the <Your_Password> for "secret".

Once you have the tenant id, subscription id, application id ("key"), and
password ("secret"), you can create an AzureNodeDriver:

.. literalinclude:: /examples/compute/azure_arm/instantiate.py
   :language: python

Alternate Cloud Environments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can select an alternate cloud environment using the "cloud_environment"
parameter to AzureNodeDriver constructor.  Available alternate cloud
environments are 'AzureChinaCloud', 'AzureUSGovernment' and 'AzureGermanCloud'.
You can also supply explicit endpoints by providing a dict with the keys
'resourceManagerEndpointUrl', 'activeDirectoryEndpointUrl',
'activeDirectoryResourceId' and 'storageEndpointSuffix'.

API Docs
--------

.. autoclass:: libcloud.compute.drivers.azure_arm.AzureNodeDriver
    :members:
    :inherited-members:

.. _`Azure Virtual Machines`: http://azure.microsoft.com/en-us/services/virtual-machines/

.. _`Azure Resource Management`: https://msdn.microsoft.com/en-us/library/azure/Dn948464.aspx
