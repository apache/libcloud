Libvirt Compute Driver Documentation
====================================

.. note::

    Libvirt driver in current version of Libcloud is still experimental and
    doesn't support advanced functionality like creating a node and so on.

`libvirt`_ is an open source toolkit for managing different hypervisors. It
ca be used to manage Xen, KVM, Vmware ESX, QEMU and many other hypervisors.

.. figure:: /_static/images/provider_logos/libvirt.png
    :align: center
    :width: 200
    :target: http://libvirt.org

For full list of the supported hypervisors, please see the
`Hypervisor drivers <http://libvirt.org/drivers.html#hypervisor>`_ page.

Requirements
------------

To be able to use this driver you need to install libvirt client and
`libvirt-python`_ Python package.

Libvirt client is available in standard package repositories of most popular
Linux distributions which means you can install it using your distribution's
package manager.

Example #1 - Ubuntu, Debian, etc. (apt-get):

.. sourcecode:: bash

    sudo apt-get install libvirt-client

Example #2 - Fedora, RHEL, etc. (yum):

.. sourcecode:: bash

    sudo yum install libvirt-client

Python package can be installed using pip:

.. sourcecode:: bash

    pip install libvirt-python

Connecting to a hypervisor
--------------------------

To instantiate the driver and connect to a hypervisor, you need to pass ``uri``
argument to the driver constructor.

This argument tells the driver which libvirt driver (qemu, xen, virtualbox,
etc.) this connection refers to. For a full list of supported URIs, please
refer to the `Connection URIs <http://libvirt.org/uri.html>` page.

Example 1 - Connecting to QEMU and KVM hypervisor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example shows how to connect to a local QEMU or KVM instance.

.. literalinclude:: /examples/compute/libvirt/connect_qemu_kvm.py
   :language: python

For more details and information on how to connect to a remote instance, please
see `Connections to QEMU driver <http://libvirt.org/drvqemu.html#uris>`_ page.

Example 2 - Connecting to Virtualbox hypervisor
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example shows how to connect to a local Virtualbox instance.

.. literalinclude:: /examples/compute/libvirt/connect_virtualbox.py
   :language: python

For more details and information on how to connect to a remote instance, please
see `VirtualBox hypervisor driver <http://libvirt.org/drvvbox.html>`_ page.

.. _`libvirt`: http://libvirt.org
.. _`libvirt-python`: https://pypi.python.org/pypi/libvirt-python

Enabling libvirt debug mode
---------------------------

To enable libvirt debug mode, simply set ``LIBVIRT_DEBUG`` environment
variable.

For example:

.. sourcecode:: bash

    LIBVIRT_DEBUG=1 python my_script.py

When debug mode is enabled, libvirt client will print all kind of debugging
information to the standard error.

API Docs
--------

.. autoclass:: libcloud.compute.drivers.libvirt_driver.LibvirtNodeDriver
    :members:
    :inherited-members:
