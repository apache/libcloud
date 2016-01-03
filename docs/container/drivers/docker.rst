Docker Container Driver Documentation
=====================================

`Docker`_ containers wrap up a piece of software in a complete filesystem that contains everything it needs to run:
code, runtime, system tools, system libraries – anything you can install on a server. This guarantees that it will always run the same,
regardless of the environment it is running in.

.. figure:: /_static/images/provider_logos/docker.png
    :align: center
    :width: 300
    :target: http://docker.io/

Instantiating the driver
------------------------

.. literalinclude:: /examples/container/docker/instantiate_driver.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.container.drivers.docker.DockerContainerDriver
    :members:
    :inherited-members:

.. _`Docker`: https://docker.io/