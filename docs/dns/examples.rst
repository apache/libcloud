DNS Examples
============

Create an 'A' record for all your compute nodes
-----------------------------------------------

This example creates a new ``mydomain2.com`` zone at Zerigo and an A record
for all your Rackspace nodes. Value for the A record is the Node's first
public IP address.

.. literalinclude:: /examples/dns/create_a_record_for_all_rackspace_nodes.py
   :language: python
