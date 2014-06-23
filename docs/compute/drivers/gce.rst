Google Compute Engine Driver Documentation
==========================================

`Google Cloud Platform Compute Engine`_ gives users the ability to run
large-scale workloads on virtual machines hosted on Google's infrastructure.
It is a part of Google Cloud Platform.

.. figure:: /_static/images/provider_logos/gcp.png
    :align: center
    :width: 500
    :target: https://cloud.google.com/

Google Compute Engine features:

* High-performance virtual machines
* Minute-level billing (10-minute minimum)
* Fast VM provisioning
* Native Load Balancing

Connecting to Google Compute Engine
-----------------------------------
Libcloud supports two different methods for authenticating to Compute Engine:
`Service Account`_ and `Installed Application`_

Which one should I use?

* Service Accounts are generally better suited for automated systems, cron
  jobs, etc.  They should be used when access to the application/script is
  limited and needs to be able to run with limited intervention.

* Installed Application authentication is often the better choice when
  creating an application that may be used by third-parties interactively. For
  example, a desktop application for managing VMs that would be used by many
  different people with different Google accounts.

Once you have set up the authentication as described below, you pass the
authentication information to the driver as described in `Examples`_


Service Account
~~~~~~~~~~~~~~~

To set up Service Account authentication:

1. Follow the instructions at 
   https://developers.google.com/console/help/new/#serviceaccounts
   to create and download a PKCS-12 private key.
2. Convert the PKCS-12 private key to a .pem file using the following:
   ``openssl pkcs12 -in YOURPRIVKEY.p12 -nodes -nocerts 
   | openssl rsa -out PRIV.pem``
3. Move the .pem file to a safe location
4. You will need the Service Account's "Email Address" and the path to the
   .pem file for authentication.
5. You will also need your "Project ID" which can be found by clicking on the
   "Overview" link on the left sidebar.

Installed Application
~~~~~~~~~~~~~~~~~~~~~

To set up Installed Account authentication:

1. Go to the `Google Developers Console`_
2. Select your project
3. In the left sidebar, go to "APIs & auth"
4. Click on "Credentials" then "Create New Client ID"
5. Select "Installed application" and "Other" then click "Create Client ID"
6. For authentication, you will need the "Client ID" and the "Client Secret"
7. You will also need your "Project ID" which can be found by clicking on the
   "Overview" link on the left sidebar.

Examples
--------

Additional example code can be found in the "demos" directory of Libcloud here:
https://github.com/apache/libcloud/blob/trunk/demos/gce_demo.py

1. Getting Driver with Service Account authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/gce/gce_service_account.py

2. Getting Driver with Installed Application authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/gce/gce_installed_application.py

3. Getting Driver using a default Datacenter (Zone)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/gce/gce_datacenter.py

API Docs
--------

.. autoclass:: libcloud.compute.drivers.gce.GCENodeDriver
    :members:
    :inherited-members:

.. _`Google Cloud Platform Compute Engine`: https://cloud.google.com/products/compute-engine/
.. _`Google Developers Console`: https://cloud.google.com/console
