DigitalOcean Spaces Storage Driver Documentation
================================================

`Spaces`_ is an `S3-interoperable`_ object storage service from cloud provider
DigitalOcean.

Connecting to Spaces
--------------------

To connect to DigitalOcean Spaces you need an access key and secret key. These
can be retrieved on the "`Applications & API`_" page of the DigitalOcean control
panel.

Instantiating a driver
~~~~~~~~~~~~~~~~~~~~~~

Once you have obtained your credentials you can instantiate the driver as shown
below.

.. literalinclude:: /examples/storage/digitalocean_spaces/instantiate.py
   :language: python

Spaces supports both the v2 and v4 AWS signature types. By default, this driver
will use v2. You can configure it to use v4 by passing the ``signature_version``
argument when instantiating the driver as shown below.

.. literalinclude:: /examples/storage/digitalocean_spaces/v4sig.py
   :language: python

Specifying canned ACLs
~~~~~~~~~~~~~~~~~~~~~~

Spaces supports a limited set of canned ACLs. In order to specify an ACL when
uploading an object, you can pass an ``extra`` argument with the ``acl``
attribute to the upload methods.

For example:

.. literalinclude:: /examples/storage/digitalocean_spaces/upload_object_acls.py
   :language: python

At this time, valid values for this attribute are only:

* ``private`` (default)
* ``public-read``

API Docs
--------

.. autoclass:: libcloud.storage.drivers.digitalocean_spaces.DigitalOceanSpacesStorageDriver
    :members:
    :inherited-members:

.. _`Spaces`: https://www.digitalocean.com/products/object-storage/
.. _`Applications & API`: https://cloud.digitalocean.com/settings/api/tokens
.. _`S3-interoperable`: https://developers.digitalocean.com/documentation/spaces/