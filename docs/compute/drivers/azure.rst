Azure ASM Compute Driver Documentation
======================================

Azure driver allows you to integrate with Microsoft `Azure Virtual Machines`_
service using the `Azure Service Management`_ (ASM) API.  This is the "Classic"
API, please note that it is incompatible with the newer
`Azure Resource Management`_ (ARM) API, which is provideb by the `azure_arm`_ driver.

.. figure:: /_static/images/provider_logos/azure.jpg
    :align: center
    :width: 300
    :target: http://azure.microsoft.com/en-us/services/virtual-machines/

Azure Virtual Machine service allows you to launch Windows and Linux virtual
servers in many datacenters across the world.

Connecting to Azure
-------------------

To connect to Azure you need  your subscription ID and certificate file.

Generating and uploading a certificate file and obtaining subscription ID
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To be able to connect to the Azure, you need to generate a X.509 certificate
which is used to authenticate yourself and upload it to the Azure Management
Portal.

On Linux, you can generate the certificate file using the commands shown below:

.. sourcecode:: bash

    openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout azure_cert.pem -out azure_cert.pem
    openssl x509 -inform pem -in azure_cert.pem -outform der -out azure_cert.cer

For information on how to generate certificate on Windows, see
`Create and Upload a Management Certificate for Azure <https://msdn.microsoft.com/en-us/library/azure/gg551722.aspx>`_ page.

Once you have generated the certificate, go to the Azure Management Portal and
click Settings -> Management Certificate -> Upload as shown on the screenshot
below.

.. figure:: /_static/images/misc/azure_upload_certificate_file.png
    :align: center
    :width: 900

In the upload Windows, select the generated ``.cer`` file (``azure_cert.cer``).

Instantiating a driver
~~~~~~~~~~~~~~~~~~~~~~

Once you have generated the certificate file and obtained your subscription ID
you can instantiate the driver as shown below.

.. literalinclude:: /examples/compute/azure/instantiate.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.compute.drivers.azure.AzureNodeDriver
    :members:
    :inherited-members:

.. _`Azure Virtual Machines`: http://azure.microsoft.com/en-us/services/virtual-machines/

.. _`Azure Service Management`: https://msdn.microsoft.com/en-us/library/azure/dn948465.aspx

.. _`Azure Resource Management`: https://msdn.microsoft.com/en-us/library/azure/Dn948464.aspx

.. _`azure_arm`: azure_arm.html
