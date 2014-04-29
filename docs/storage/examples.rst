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
