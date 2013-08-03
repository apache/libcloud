Welcome to Apache Libcloud's documentation!
===========================================

.. note::

    Right now we're in the progress of migrating our existing documentation to
    Sphinx, so this may be incomplete. We apologize for the inconvenience and we
    hope the upcoming awesomeness will make up for it.

.. note::

    Unless noted otherwise, all of the examples in the documentation are
    licensed under the `Apache 2.0 license`_.

Apache Libcloud is a Python library which abstracts away the differences
between multiple cloud providers. It current can manage four different cloud
resources:

* :doc:`Cloud servers </compute/index>` - services such as Amazon EC2 and
  RackSpace CloudServers
* :doc:`Cloud object storage </storage/index>` - services such as Amazon S3 and
  Rackspace CloudFiles
* :doc:`Load Balancers as a Service </loadbalancer/index>`
* :doc:`DNS as a Service </dns/index>`

.. toctree::
    :glob:
    :maxdepth: 2
    :hidden:

    compute/*
    storage/*
    loadbalancer/*
    dns/*
    other/*

.. _`Apache 2.0 license`: https://www.apache.org/licenses/LICENSE-2.0.html
