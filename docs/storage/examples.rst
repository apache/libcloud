:orphan:

Storage Examples
================

Specify meta-data when uploading an object
------------------------------------------

Most of the providers allow you to associate arbitrary key-value pairs
(meta-data) with every uploaded object. This example shows how to do that in
Libcloud.

.. literalinclude:: /examples/storage/upload_with_metadata.py
   :language: python

As you can see in the example above, meta-data is specified by including
``meta_data`` key in the ``extra`` dictionary argument which gets passed
to all the upload methods.

Download part of an object
--------------------------

To perform a partial (range) object download, you can utilize new
:meth:`libcloud.storage.base.StorageDriver.download_object_range`
and :meth:`libcloud.storage.base.StorageDriver.download_object_range_as_stream`
methods which have been added in Libcloud v3.0.0.

``start_bytes`` and ``end_bytes`` behave in the same manner as Python
indexing which means that ``start_bytes`` is inclusive and ``end_bytes``
is non-inclusive.

For example, if the object content is ``0123456789``, here is what
would be returned for various values of start and end bytes arguments:

* start_bytes=0, end_bytes=1 -> 0
* start_bytes=0, end_bytes=2 -> 01
* start_bytes=5, end_bytes=6 -> 5
* start_bytes=5, end_bytes=10 -> 56789

.. literalinclude:: /examples/storage/partial_object_download.py
   :language: python

Create a backup of a directory and directly stream it to CloudFiles
-------------------------------------------------------------------

.. literalinclude:: /examples/storage/create_directory_backup_stream_to_cf.py
   :language: python

Efficiently download multiple files using gevent
------------------------------------------------

.. literalinclude:: /examples/storage/concurrent_file_download_using_gevent.py
   :language: python

Publishing a static website using CloudFiles driver
---------------------------------------------------

.. note::
    This example works with Libcloud version 0.11.0 and above.

.. literalinclude:: /examples/storage/publish_static_website_on_cf.py
   :language: python
