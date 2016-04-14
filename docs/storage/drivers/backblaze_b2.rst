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

Keep in mind that the service is currently in public beta and only users who
have signed up and received beta access can use it. To sign up for the beta
access, visit their website mentioned above.

Instantiating a driver
----------------------

To instantiate the driver you need to pass your account id and application key
to the driver constructor as shown below.

To access the account id, once we have admitted you into the beta you can login
to https://secure.backblaze.com/user_signin.htm, then click "buckets" and
"show account id and application key".

.. literalinclude:: /examples/storage/backblaze_b2/instantiate.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.storage.drivers.backblaze_b2.BackblazeB2StorageDriver
    :members:
    :inherited-members:

.. _`Backblaze`: https://www.backblaze.com/
.. _`Backblaze B2`: https://www.backblaze.com/b2/cloud-storage.html
