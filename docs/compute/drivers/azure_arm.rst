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
[Azure cross-platform CLI v2](https://github.com/Azure/azure-cli), use ``az account list`` to get these
values.

Creating a Service Principal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. sourcecode:: bash

  az login
  az ad sp create-for-rbac -p "$AZURE_KEY_FILE" --name "$display_name" --password "$secret" --role 'API Management Service Contributor' --expanded-view

Redundant rules: # TODO: Remove this

  az ad app create --display-name $display_name --homepage "$homepage" --identifier-uris "$homepage" --password "$secret"
  az ad sp create --id "$appId" # see output of^ for $appId
  az role definition list
  azure role assignment create --objectId "<Object_Id>" -o Owner -c /subscriptions/{subscriptionId}/

Instantiating a driver
~~~~~~~~~~~~~~~~~~~~~~

Once you have the tenant id, subscription id, application id ("client"), and
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
