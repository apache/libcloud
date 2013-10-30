DNS Examples
============

Create an 'A' record for all your compute nodes
-----------------------------------------------

This example creates a new ``mydomain2.com`` zone at Zerigo and an A record
for all your Rackspace nodes. Value for the A record is the Node's first
public IP address.

.. literalinclude:: /examples/dns/create_a_record_for_all_rackspace_nodes.py
   :language: python

Create a record with a custom TTL
---------------------------------

This example shows how to create a record with a custom TTL. Keep in mind that
not all of the providers support setting a custom, per record TTL.

.. literalinclude:: /examples/dns/create_record_custom_ttl.py
   :language: python

Create a MX record and specify a priority
-----------------------------------------

Some record types such as ``MX`` and ``SRV`` allow you to specify priority. This
example shows how to do that.

.. literalinclude:: /examples/dns/create_record_with_priority.py
   :language: python

Export Libcloud Zone to BIND zone format
----------------------------------------

.. note::

    This functionality is only available in Libcloud 0.14.0 and above.

This example shows how to export Libcloud Zone to bind format.

Keep in mind that generated bind zone file content doesn't contain ``SOA`` and
``NS`` records. This should work fine if you just want to import this file
using a DNS provider web interface, but if you want to use it with BIND you
need to manually add those records.

Printing the output
~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/dns/export_zone_to_bind_format.py
   :language: python

Saving output into a file
~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/dns/export_zone_to_bind_format_file.py
   :language: python
