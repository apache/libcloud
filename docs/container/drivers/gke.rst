Google Container Driver Documentation
============================================

`Google Container Platform`_ is a Kubernetes hosting service, provided by Google.
Docker-native tools and elastic hosts make deploying on Google Cloud as easy as running Docker on your laptop.
There is no special software to install or configure.
Mix Kubernetes containers with container-native Linux to extend the benefits of containerization to legacy applications and stateful services.

Examples
--------

Additional example code can be found in the "demos" directory of Libcloud here:
https://github.com/apache/libcloud/blob/trunk/demos/gce_demo.py

1. Getting Driver with Service Account authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/gce/gce_service_account.py


API Docs
--------

.. autoclass:: libcloud.container.drivers.gke.GKEContainerDriver
    :members:
    :inherited-members:

.. _`Google Container Platform`: https://cloud.google.com/container-engine/
