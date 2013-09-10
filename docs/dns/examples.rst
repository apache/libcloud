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
