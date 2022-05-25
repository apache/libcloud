Google Compute Engine Driver Documentation
==========================================

`Google Compute Engine`_ gives users the ability to run
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
`Service Account`_, `Installed Application`_ and `Internal Authentication`_.

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
  authorization token. The only value required for this type of
  authorization is your Project ID.

Once you have set up the authentication as described below, you pass the
authentication information to the driver as described in `Examples`_. Also
bear in mind that large clock drift (difference in time) between authenticating
host and google will cause authentication to fail.

Service Account
~~~~~~~~~~~~~~~

To set up Service Account authentication, you will need to download the
corresponding private key file in either the new JSON (preferred) format, or
the legacy P12 format.

1. Go to Google Cloud Console (https://console.cloud.google.com/) and create a
   new project (https://console.cloud.google.com/projectcreate) or re-use an
   existing one.

.. figure:: /_static/images/misc/gce/create_service_account.png
    :align: center
    :width: 500

2. Select the existing or newly created project and go to IAM & Admin ->
   Service Accounts -> Create service account to create a new service account.
   Select "Furnish a new private key" to create and download new private key you will
   use to authenticate.

   a. If you opt for the new preferred JSON format, download the file and
      save it to a secure location.

   b. If you opt to use the legacy P12 format:

      Convert the private key to a .pem file using the following:
      ``openssl pkcs12 -in YOURPRIVKEY.p12 -nodes -nocerts
      | openssl rsa -out PRIV.pem``

      Move the .pem file to a safe location


.. figure:: /_static/images/misc/gce/iam_and_roles.png
    :align: center
    :width: 500

.. figure:: /_static/images/misc/gce/create_service_account.png
    :align: center
    :width: 500

3. You will need the Service Account's "Email Address" and the path to the
   key file for authentication.

.. figure:: /_static/images/misc/gce/view_service_accounts.png
    :align: center
    :width: 500

4. You will also need your "Project ID" (a string, not a numerical value) that
   can be found by clicking on the "Overview" link on the left sidebar.

.. figure:: /_static/images/misc/gce/project_dashboard.png
    :align: center
    :width: 500

5. You will also need to have billing information associated and enabled for
   that project. If billing is not yet enabled for that project an error
   message similar to the one below will be printed when you first run the code
   which uses GCE driver:

.. sourcecode:: python

    libcloud.common.google.GoogleBaseError: {u'domain': u'usageLimits', u'message': u'Access Not Configured. Compute Engine API has not been used in project 1029894677594 before or it is disabled. Enable it by visiting https://console.developers.google.com/apis/api/compute.googleapis.com/overview?project=1029894677594 then retry. If you enabled this API recently, wait a few minutes for the action to propagate to our systems and retry.', u'reason': u'accessNotConfigured', u'extendedHelp': u'https://console.developers.google.com/apis/api/compute.googleapis.com/overview?project=YYYYYYYY'}

You can simply follow the link in the error message to configure and enable
billing.

Installed Application
~~~~~~~~~~~~~~~~~~~~~

To set up Installed Account authentication:

1. Go to the `Google Developers Console`_
2. Select your project
3. In the left sidebar, go to "APIs & auth"
4. Click on "Credentials" then "Create New Client ID"
5. Select "Installed application" and "Other" then click "Create Client ID"
6. For authentication, you will need the "Client ID" and the "Client Secret"
7. You will also need your "Project ID" (a string, not a numerical value) that
   can be found by clicking on the "Overview" link on the left sidebar.

Internal Authentication
~~~~~~~~~~~~~~~~~~~~~~~

To use GCE's internal metadata service to authenticate, simply specify
your Project ID and let the driver handle the rest. See the
`5. Using GCE Internal Authorization`_ example below.

Accessing Google Cloud services from your Libcloud nodes
--------------------------------------------------------
In order for nodes created with libcloud to be able to access or manage other
Google Cloud Platform services, you will need to specify a list of Service
Account Scopes.  By default libcloud will create nodes that only allow
read-only access to Google Cloud Storage. A few of the examples below
illustrate how to use Service Account Scopes.

Examples
--------

Keep in mind that a lot of the driver methods depend on the zone / location
being set.

For that reason, you are advised to pass ``datacenter`` argument to the driver
constructor. This value should contain a name of the zone where you want your
operations to be performed (e.g. ``us-east1-b``).

Some of the methods allow this value to be overridden on per method invocation
basis - either by specifying ``zone`` or ``location`` method argument.

Additional example code can be found in the "demos" directory of Libcloud here:
https://github.com/apache/libcloud/blob/trunk/demos/gce_demo.py

1. Getting Driver with Service Account authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With local key file:

.. literalinclude:: /examples/compute/gce/gce_service_account.py

With Service Account credentials as dict:

.. literalinclude:: /examples/compute/gce/gce_service_account_infile.py

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

6. Using deploy_node() functionality
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/gce/deploy_node.py

API Docs
--------

.. autoclass:: libcloud.compute.drivers.gce.GCENodeDriver
    :members:
    :inherited-members:

.. _`Google Compute Engine`: https://cloud.google.com/products/compute-engine/
.. _`Google Developers Console`: https://cloud.google.com/console
