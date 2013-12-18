:orphan:

SSH key pair management
=======================

.. note::

    This functionality is only available as part of the base API in Libcloud
    0.14.0 and above. Previously it was available on some drivers through
    the extension methods.

Key pair management functionality allows you to manage SSH key pairs on your
account.

This includes the following functionality:

* listing all the available key pairs on your account
  (:func:`libcloud.compute.base.NodeDriver.list_key_pairs`)
* retrieve information (fingerprint, public key) about a sigle key pair
  (:func:`libcloud.compute.base.NodeDriver.get_key_pair`)
* creating a new key pair
  (:func:`libcloud.compute.base.NodeDriver.create_key_pair`)
* importing an existing public key
  (:func:`libcloud.compute.base.NodeDriver.import_key_pair_from_string`
  and :func:`libcloud.compute.base.NodeDriver.import_key_pair_from_file`)
* deleting an existing key pair
  (:func:`libcloud.compute.base.NodeDriver.delete_key_pair`)

Creating a new key pair
-----------------------

This example shows how to create a new key pair using
:func:`libcloud.compute.base.NodeDriver.create_key_pair` method.

To generate a new key pair, you only need to specify a `name` argument and the
provider will automatically generate a new key pair for you. Private key which
has been generated on your behalf is available in the value returned by the
create_key_pair method.

.. literalinclude:: /examples/compute/create_key_pair.py
   :language: python

Importing an existing key pair
------------------------------

If you already have an existing key pair you would like to use, you can use
:func:`libcloud.compute.base.NodeDriver.import_key_pair_from_file` and
:func:`libcloud.compute.base.NodeDriver.import_key_pair_from_string` method
to import a public component of this pair.

.. literalinclude:: /examples/compute/import_key_pair_from_file.py
   :language: python

.. literalinclude:: /examples/compute/import_key_pair_from_string.py
   :language: python
