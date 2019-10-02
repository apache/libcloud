Backblaze B2 Storage Driver Documentation
=========================================

`Backblaze`_ is an online backup tool that allows Windows and Mac OS X users to
back up their data to an offsite data center.

`Backblaze B2`_ is their cloud object storage offering similar to Amazon S3 and
other object storage services.

.. figure:: /_static/images/provider_logos/backblaze.png
    :align: center
    :width: 300
    :target: https://www.backblaze.com/b2/cloud-storage.html

Instantiating a driver
----------------------

To instantiate the driver you need to pass your key id and application key to
the driver constructor as shown below.

To access the credentials, you can login to
https://secure.backblaze.com/user_signin.htm, then click "App Keys" or go
to https://secure.backblaze.com/app_keys.htm directly.

``keyID`` serves as the first and ``applicationKey`` as the second argument to
the driver constructor.

.. literalinclude:: /examples/storage/backblaze_b2/instantiate.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.storage.drivers.backblaze_b2.BackblazeB2StorageDriver
    :members:
    :inherited-members:

.. _`Backblaze`: https://www.backblaze.com/
.. _`Backblaze B2`: https://www.backblaze.com/b2/cloud-storage.html
