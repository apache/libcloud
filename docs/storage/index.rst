Object Storage
==============

.. note::

    Object Storage API is available in Libcloud 0.5.0 and higher.

Storage API allows you to manage cloud object storage (not to be confused with
cloud block storage) and services such as Amazon S3, Rackspace CloudFiles,
Google Storage and others.

Besides managing cloud object storage, storage component also exposes simple
CDN management functionality.

Terminology
-----------

* :class:`~libcloud.storage.base.Container` - represents a container which can
  contain multiple objects. You can think of it as a folder on a file system.
  Difference between container and a folder on file system is that containers
  cannot be nested. Some APIs and providers (e.g. AWS) refer to it as a Bucket.
* :class:`~libcloud.storage.base.Object` - represents an object or so called
  BLOB.

Supported Providers
-------------------

For a list of supported providers see :doc:`supported providers page
</storage/supported_providers>`.

Examples
--------

We have :doc:`examples of several common patterns </storage/examples>`.

API Reference
-------------

For a full reference of all the classes and methods exposed by the storage
API, see :doc:`this page </storage/api>`.
