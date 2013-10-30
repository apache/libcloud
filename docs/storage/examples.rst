Storage Examples
================

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
