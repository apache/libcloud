Welcome to Apache Libcloud's documentation!
===========================================

Apache Libcloud is a Python library which hides differences between different
cloud provider APIs and allows you to manage different cloud resources through
a unified and easy to use API.

Resource you can manage with Libcloud are divided in the following categories:

* :doc:`Cloud Servers and Block Storage </compute/index>` - services such as Amazon EC2 and
  RackSpace CloudServers
* :doc:`Cloud Object Storage and CDN </storage/index>` - services such as Amazon S3 and
  Rackspace CloudFiles
* :doc:`Load Balancers as a Service </loadbalancer/index>` - services such as Amazon Elastic Load Balancer and GoGrid LoadBalancers
* :doc:`DNS as a Service </dns/index>` - services such as Amazon Route 53 and Zerigo

.. figure:: /_static/images/supported_providers.png
    :align: center

    A subset of supported providers in Libcloud.

Documentation
=============

Main
----

.. toctree::
    :glob:
    :maxdepth: 3

    getting_started
    changelog
    supported_providers
    compute/index
    storage/index
    loadbalancer/index
    dns/index
    upgrade_notes
    troubleshooting
    faq
    other/*

Developer Information
---------------------

.. toctree::
    :glob:
    :maxdepth: 3

    developer_information
    development

Committer Guide
---------------

.. toctree::
    :glob:
    :maxdepth: 3

    committer_guide

.. note::

    Unless noted otherwise, all of the examples and code snippters in the
    documentation are licensed under the `Apache 2.0 license`_.

.. _`Apache 2.0 license`: https://www.apache.org/licenses/LICENSE-2.0.html
