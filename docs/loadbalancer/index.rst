Load Balancer
=============

.. note::

    Load Balancer API is available in Libcloud 0.5.0 and higher.

Load Balancer API allows you to manage Load Balancers as a service and services
such as Rackspace Cloud Load Balancers, GoGrid Load Balancers and Ninefold Load
Balancers.

Terminology
-----------

* **LoadBalancer** - represents a load balancer instance.
* **Member** - represents a load balancer member.
* **Algorithm** - represents a load balancing algorithm (round-robin, random,
  least connections, etc.).

Supported Providers
-------------------

For a list of supported providers see :doc:`supported providers page
</loadbalancer/supported_providers>`.

Examples
--------

We have :doc:`examples of several common patterns </loadbalancer/examples>`.

API Reference
-------------

There is a reference to :doc:`all the methods on the base loadbalancer driver
</loadbalancer/api/>`.
