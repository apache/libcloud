Container
=========

.. note::

    Container API is available in Libcloud 0.21.0 and higher.

Container API allows users to install and deploy containers onto container based virtualization platforms. This is designed to target both
on-premise installations of software like Docker and Rkt as well as interfacing with Cloud Service Providers that offer Container-as-a-Service APIs

Terminology
-----------

* :class:`~libcloud.container.base.ContainerImage` - Represents an image that can be deployed, like an application or an operating system
* :class:`~libcloud.container.base.Container` - Represents a deployed container image running on a container host


Supported Providers
-------------------

For a list of supported providers see :doc:`supported providers page
</container/supported_providers>`.

Examples
--------

We have :doc:`examples of several common patterns </container/examples>`.

API Reference
-------------

For a full reference of all the classes and methods exposed by the Container
API, see :doc:`this page </container/api>`.