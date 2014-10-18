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
* Persistent block storage (SSD and standard)
* Native Load Balancing

Connecting to Google Compute Engine
-----------------------------------
Libcloud supports three different methods for authenticating:
`Service Account`_ and `Installed Application`_ and `Internal Authentication_`

Which one should I use?

* Service Accounts are generally better suited for automated systems, cron
  jobs, etc.  They should be used when access to the application/script is
  limited and needs to be able to run with limited intervention.

* Installed Application authentication is often the better choice when
  creating an application that may be used by third-parties interactively. For
  example, a desktop application for managing VMs that would be used by many
  different people with different Google accounts.

* If you are running your code on an instance inside Google Compute Engine,
  the GCE driver will consult the internal metadata service to obtain an
  authorization token. The only parameter required for this type of
  authorization is your Project ID.

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

Internal Authentication
~~~~~~~~~~~~~~~~~~~~~~~

To use GCE's internal metadata service to authenticate, simply specify
your Project ID and let the driver handle the rest.  See the `Examples`_
below for a sample.

Accessing Google Cloud services from your Libcloud nodes
--------------------------------------------------------
In order for nodes created with libcloud to be able to access or manage other
Google Cloud Platform services, you will need to specify a list of Service
Account Scopes.  By default libcloud will create nodes that only allow
read-only access to Google Cloud Storage. A few of the examples below
illustrate how to use Service Account Scopes.

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

4. Specifying Service Account Scopes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/gce/gce_service_account_scopes.py

5. Using GCE Internal Authorization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/gce/gce_internal_auth.py

API Docs
--------

.. autoclass:: libcloud.compute.drivers.gce.GCENodeDriver
    :members:
    :inherited-members:

.. _`Google Cloud Platform Compute Engine`: https://cloud.google.com/products/compute-engine/
.. _`Google Developers Console`: https://cloud.google.com/console
