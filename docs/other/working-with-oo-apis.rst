Working with the object oriented APIs
=====================================

To make it easier for the end user, Libcloud components expose a fully
object-oriented API.

This means that besides the driver object you also work with ``NodeImage``,
and ``NodeSize`` object in the compute API, ``Container`` and ``Object``
object in the Storage API, ``Zone`` and ``Record`` object in the DNS API
and so on.

Methods which operate on those resources usually require you to pass in an
instance of the resource you want to manipulate or work with and not just an
id.

To obtain a reference to this resource, Libcloud providers corresponding get
and / or list methods.

A couple of examples are shown bellow.

Example 1 - listing records for a zone with a known id
------------------------------------------------------

.. literalinclude:: /examples/dns/list_zone_records.py
   :language: python

In this example, :func:`driver.get_zone` method call results in an HTTP call.

Example 2 - creating an EC2 instance with a known ``NodeSize`` and ``NodeImage`` id
-----------------------------------------------------------------------------------

.. literalinclude:: /examples/compute/create_ec2_node.py
   :language: python

In this example, both :func:`driver.list_sizes` an :func:`driver.list_images`
method calls result in an HTTP call.

As you can see above, most of those getter methods retrieve extra information
about the resource from the provider API and result in an HTTP request.

There are some cases when you might not want this:

* You don't care if a resource doesn't exist
* You don't care about the extra attributes
* You want to avoid an extra HTTP request
* You want to avoid holding a reference to the resource object

If that is true for you, you can directly instantiate a resource with a known
id. You can see how to do this in the examples bellow.

Example 1 - listing records for a zone with a known id
------------------------------------------------------

.. literalinclude:: /examples/dns/list_zone_records_manual_instantiation.py
   :language: python

Example 2 - creating an EC2 instance with a known ``NodeSize`` and ``NodeImage`` id
-----------------------------------------------------------------------------------

.. literalinclude:: /examples/compute/create_ec2_node_manual_instantiation.py
   :language: python

Example 3 - creating an EC2 instance with an IAM profile
--------------------------------------------------------

.. literalinclude:: /examples/compute/create_ec2_node_iam.py
   :language: python
