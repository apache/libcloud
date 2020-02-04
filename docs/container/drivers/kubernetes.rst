Kubernetes Documentation
========================

.. note::

    This Kubernetes driver will be subject to change from community feedback. How to map the core assets (pods, clusters) to API
    entities will be subject to testing and further community feedback.

Kubernetes is an open source orchestration system for Docker containers. It handles scheduling onto nodes in a compute cluster and actively manages workloads to ensure that their state matches the users declared intentions. Using the concepts of "labels" and "pods",
it groups the containers which make up an application into logical units for easy management and discovery.

.. figure:: /_static/images/provider_logos/kubernetes.png
    :align: center
    :width: 300
    :target: http://kubernetes.io/

Authentication
--------------

Authentication currently supported with the following methods:

* Client certificate auth (recommended) - https://kubernetes.io/docs/reference/access-authn-authz/authentication/#x509-client-certs
* Bearer token auth - https://kubernetes.io/docs/reference/access-authn-authz/authentication/#static-token-file
* Basic HTTP Authentication (deprecated) - https://kubernetes.io/docs/reference/access-authn-authz/authentication/#static-password-file
* No authentication (testing only)

Instantiating the driver
------------------------

.. literalinclude:: /examples/container/kubernetes/instantiate_driver.py
   :language: python

Instantiating the driver (minikube installation - cert file auth)
-----------------------------------------------------------------

This example shows how to connect to a local minikube Kubernetes cluster
which utilizes certifcate based authentication.

.. literalinclude:: /examples/container/kubernetes/instantiate_driver_minikube_cert_auth.py
   :language: python

Instantiating the driver (minikube installation - basic auth)
-------------------------------------------------------------

This example shows how to connect to a local minikube Kubernetes cluster
which utilizes basic auth authentication.

When using basic auth, you need to start the minikube as shown below.

.. sourcecode:: bash

    $ cat users.csv
    pass123,user1,developers

.. sourcecode:: python

    # Mount a share with a local users file
    minikube mount /home/libcloud/users.csv:/var/lib/docker/users.csv

    # Start miniube
    minikube --extra-config=apiserver.basic-auth-file=/var/lib/docker/users.csv start

.. literalinclude:: /examples/container/kubernetes/instantiate_driver_minikube_basic_auth.py
   :language: python

-------------------------------------

Docker Hub Client :class:`~libcloud.container.utils.docker.HubClient` is a shared utility class for interfacing to the public Docker Hub Service.

You can use this class for fetching images to deploy to services like ECS

.. literalinclude:: /examples/container/kubernetes/docker_hub.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.container.drivers.kubernetes.KubernetesContainerDriver
    :members:
    :inherited-members:
