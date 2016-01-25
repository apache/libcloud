Backup
======

.. note::

    Backup API is available in Libcloud 1.0.0-pre1 and higher.

.. note::

    This driver is **experimental** - please use to test functionality and develop new driver instances, not for production use.

Backup API allows you to manage Backup as A Service and services such as EBS Snaps,
GCE volume snap and dimension data backup.

Terminology
-----------

* :class:`~libcloud.backup.base.BackupTarget` - Represents a backup target, like a Virtual Machine, a folder or a database.
* :class:`~libcloud.backup.base.BackupTargetRecoveryPoint` - Represents a copy of the data in the target, a recovery point can be
  recovered to a backup target. An inplace restore is where you recover to the same target and an out-of-place restore is where you
  recover to another target.
* :class:`~libcloud.backup.base.BackupTargetJob` - Represents a backup job running on backup target.


Supported Providers
-------------------

For a list of supported providers see :doc:`supported providers page
</backup/supported_providers>`.

Examples
--------

We have :doc:`examples of several common patterns </backup/examples>`.

API Reference
-------------

For a full reference of all the classes and methods exposed by the Backup
API, see :doc:`this page </backup/api>`.
