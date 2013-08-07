Welcome to Apache Libcloud's documentation!
===========================================

.. note::

    Right now we're in the progress of migrating our existing documentation to
    Sphinx, so this may be incomplete. We apologize for the inconvenience and we
    hope the upcoming awesomeness will make up for it.

.. note::

    Unless noted otherwise, all of the examples in the documentation are
    licensed under the `Apache 2.0 license`_.

Apache Libcloud is a Python library which hides differences between different
cloud provider APIs and allows you to manage different cloud resources through
a unified and easy to use API.

Resource you can manage with Libcloud are divided in the following categories:

* :doc:`Cloud Servers and Block Storage </compute/index>` - services such as Amazon EC2 and
  RackSpace CloudServers
* :doc:`Cloud Object Storage </storage/index>` - services such as Amazon S3 and
  Rackspace CloudFiles
* :doc:`Load Balancers as a Service </loadbalancer/index>` - services such as Amazon Elastic Load Balancer and GoGrid LoadBalancers
* :doc:`DNS as a Service </dns/index>` - services such as Amazon Route 53 and Zerigo

.. figure:: /_static/images/supported_providers.png
    :align: center

    A subset of supported providers in Libcloud.

Documentation
=============

.. toctree::
    :glob:
    :maxdepth: 3

    getting_started
    supported_providers
    compute/index
    storage/index
    loadbalancer/index
    dns/index
    troubleshooting
    faq
    other/*

.. _`Apache 2.0 license`: https://www.apache.org/licenses/LICENSE-2.0.html
