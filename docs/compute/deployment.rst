Deployment
==========

Compute part of the API exposes a simple deployment functionality through the
:func:`libcloud.compute.base.NodeDriver.deploy_node` method. This functionality is
there to help you bootstrap a new server. It allows you to perform tasks such
as:

* Install your public SSH key on the server
* Instal configuration management software
* Add an initial user account
* Install an initial set of SSL certificates and keys on the server

As noted above, this functionality is there to help you bootstrap a server
and is not a replacement for a configuration management software such as
`Chef`_ `Puppet`_, `Salt`_, `CFEngine`_ and others.

Once your server has been bootstrapped, libcloud.deploy task should be done
and replaced by other tools such as previously mentioned configuration
management software.

Deployment classes
------------------

Deployment module exposes multiple classes which make running common
bootstrap tasks such as installing a file and running a shell command
on a server easier.

All the available classes are listed bellow.

.. autoclass:: libcloud.compute.deployment.SSHKeyDeployment
.. autoclass:: libcloud.compute.deployment.FileDeployment
.. autoclass:: libcloud.compute.deployment.ScriptDeployment
.. autoclass:: libcloud.compute.deployment.ScriptFileDeployment
.. autoclass:: libcloud.compute.deployment.MultiStepDeployment

Using deployment functionality
------------------------------

This section describes how to use deployment functionality and
:func:`libcloud.compute.base.NodeDriver.deploy_node` method.

deploy_node method allows you to create a cloud server and run bootstrap
commands on it. It works in the following steps:

1. Create a server (same as ``create_node``, in fact it calls ``create_node``
   underneath)
2. Wait for the server to come online and SSH server to become available
3. Run provided bootstrap step(s) on the server

As noted above, second step waits for node to become available which means it
can take a while. If for some reason deploy_node is timing out, make sure you
are using a correct ``ssh_username``. You can troubleshoot deployment issues
using LIBCLOUD_DEBUG method which is described on the
:ref:`troubleshooting page <troubleshooting>`.

:func:`libcloud.compute.base.NodeDriver.deploy_node` takes the same base
keyword arguments as the :func:`libcloud.compute.base.NodeDriver.create_node`
method a couple of additional arguments. The most important ones are ``deploy``
and ``auth``:

* ``deploy`` argument specifies which deployment step or steps to run after the
  server has been created.
* ``auth`` arguments tells how to login in to the created server. If this
  argument is not specified it is assumed that the provider API returns a root
  password once the server has been created and this password is then used to
  log in. For more information, please see the create_node and deploy_node
  method docstring.

Examples which demonstrates how this method can be used are displayed bellow.

Run a single deploy step using ScriptDeployment class
-----------------------------------------------------

The example bellow runs a single step and installs your public key on the
server.

.. literalinclude:: /examples/compute/deployment_single_step_install_public_key.py
   :language: python

Run multiple deploy steps using MultiStepDeployment class
---------------------------------------------------------

The example bellow runs two steps on the server using ``MultiStepDeployment``
class. As a first step it installs you SSH key and as a second step it runs a
shell script.

.. literalinclude:: /examples/compute/bootstrapping_puppet_on_node.py
   :language: python

.. _`Chef`: http://www.opscode.com/chef/
.. _`Puppet`: http://puppetlabs.com/
.. _`Salt`: http://docs.saltstack.com/topics/
.. _`CFEngine`: http://cfengine.com/
