:orphan:

Deployment
==========

Compute part of the API exposes a simple deployment functionality through the
:func:`libcloud.compute.base.NodeDriver.deploy_node` method. This functionality is
there to help you bootstrap a new server. It allows you to perform tasks such
as:

* Install your public SSH key on the server
* Install configuration management software
* Add an initial user account
* Install an initial set of SSL certificates and keys on the server

As noted above, this functionality is there to help you bootstrap a server
and is not a replacement for a configuration management software such as
`Chef`_ `Puppet`_, `Salt`_, `CFEngine`_ and others.

Once your server has been bootstrapped, libcloud.deploy task should be finished
and replaced by other tools such as previously mentioned configuration
management software.

.. note::

  paramiko v2.9.0 introduced a change to prefer SHA-2 variants of RSA key
  verification algorithm.

  With this version paramiko would fail to connect to older OpenSSH
  servers which don't support this algorithm (e.g. default setup on Ubuntu
  14.04) and throw authentication error.

  Libcloud code has been updated to be backward compatible. It first tries to
  connect to the server using default preferred algorithm values and in case
  that fails, it will fall back to the old approach with SHA-2 variants
  disabled.

  This functionality can be disabled by setting
  ``LIBCLOUD_PARAMIKO_SHA2_BACKWARD_COMPATIBILITY`` environment variable to
  ``false``.

  For security reasons (to prevent possible downgrade attacks and similar) you
  are encouraged to do that in case you know you won't be connecting to any old
  OpenSSH servers.

Supported private SSH key types
-------------------------------

.. note::

  paramiko v2.7.0 introduced support for OpenSSH 6.5 style private key files
  so this section is only relevant for users using older versions of paramiko.

`paramiko`_ Python library we use for deployment only supports RSA, DSS and
ECDSA private keys in PEM format.

Since Libcloud v3.0.0, ``Ed25519`` private keys are also supported when using
paramiko 2.2.0 or higher

If you try to use key in an other format such as newer OpenSSH and PKCS#8
format an exception will be thrown and deployment will fail.

Keys which contain the following header should generally work:

* ``-----BEGIN RSA PRIVATE KEY-----``
* ``-----BEGIN DSA PRIVATE KEY-----``
* ``-----BEGIN EC PRIVATE KEY-----``

And keys which contain the following header won't work:

* ``-----BEGIN OPENSSH PRIVATE KEY-----``
* ``-----BEGIN PRIVATE KEY-----``

To generate a RSA key in a compatible format, you can use the following
commands:

.. sourcecode:: bash

    ssh-keygen -m PEM -t rsa -b 4096 -C "comment" -f ~/.ssh/id_rsa_libcloud
    # Newer versions of OpenSSH will include a header which paramiko doesn't
    # recognize so we also need to change a header to a format paramiko
    # recognizes
    sed -i "s/-----BEGIN PRIVATE KEY-----/-----BEGIN RSA PRIVATE KEY-----/g" ~/.ssh/id_rsa_libcloud
    sed -i "s/-----END PRIVATE KEY-----/-----END RSA PRIVATE KEY-----/g" ~/.ssh/id_rsa_libcloud

For details / reference, see the following issues:

* https://github.com/paramiko/paramiko/issues/1015
* https://github.com/paramiko/paramiko/issues/1363
* https://github.com/paramiko/paramiko/issues/1313

Deployment classes
------------------

Deployment module exposes multiple classes which make running common
bootstrap tasks such as installing a file and running a shell command
on a server easier.

All the available classes are listed below.

.. autoclass:: libcloud.compute.deployment.SSHKeyDeployment
.. autoclass:: libcloud.compute.deployment.FileDeployment
.. autoclass:: libcloud.compute.deployment.ScriptDeployment
.. autoclass:: libcloud.compute.deployment.ScriptFileDeployment
.. autoclass:: libcloud.compute.deployment.MultiStepDeployment

Using deployment functionality
------------------------------

This section describes how to use deployment functionality and
:func:`libcloud.compute.base.NodeDriver.deploy_node` method.

deploy_node method allows you to create a server and run bootstrap commands on
it.

This method performs the following operations:

1. Create a server (same as ``create_node``, in fact it calls ``create_node``
   underneath)
2. Wait for the server to come online and SSH server to become available
3. Run provided bootstrap step(s) on the server

As noted above, second step waits for node to become available which means it
can take a while. If for some reason deploy_node is timing out, make sure you
are using a correct ``ssh_username``. You can troubleshoot deployment issues
using ``LIBCLOUD_DEBUG`` method which is described on the
:ref:`troubleshooting page <troubleshooting>`.

:func:`libcloud.compute.base.NodeDriver.deploy_node` takes the same base
keyword arguments as the :func:`libcloud.compute.base.NodeDriver.create_node`
method and a couple of additional arguments. The most important ones are
``deploy``, ``auth`` and ``ssh_key``:

* ``deploy`` argument specifies which deployment step or steps to run after the
  server has been created.
* ``auth`` arguments tells how to login in to the created server. If this
  argument is not specified it is assumed that the provider API returns a root
  password once the server has been created and this password is then used to
  log in. For more information, please see the create_node and deploy_node
  method docstring.
* ``ssh_key`` - A path to a private SSH key file which will be used to
  authenticate. Key needs to be in a format which is supported by paramiko
  (see section on supported key types above).
* ``ssh_username`` - SSH username used to login. If not provided, it defaults
  to ``root``.
* ``ssh_port`` - Port of the SSH server. If not provided, it defaults to
  ``22``.

To view the output (stdout, stderr) and exit code of a specific deployment
step, you can access ``stdout``, ``stderr`` and ``exit_status`` instance
variables on the deployment class instance (``ScriptDeployment``,
``ScriptFileDeployment``) in question.

For example:

.. sourcecode:: python

    ...
    step = ScriptDeployment("echo whoami ; date ; ls -la")

    node = driver.deploy_node(...)

    print('stdout: %s' % (step.stdout))
    print('stderr: %s' % (step.stderr))
    print('exit_code: %s' % (step.exit_status))

Some examples which demonstrate how this method can be used are displayed
below.

Run a single deploy step using ScriptDeployment class
-----------------------------------------------------

The example below runs a single step and installs your public key on the
server.

.. literalinclude:: /examples/compute/deployment_single_step_install_public_key.py
   :language: python

Run multiple deploy steps using MultiStepDeployment class
---------------------------------------------------------

The example below runs two steps on the server using ``MultiStepDeployment``
class. As a first step it installs you SSH key and as a second step it runs a
shell script.

.. literalinclude:: /examples/compute/bootstrapping_puppet_on_node.py
   :language: python

.. _`Chef`: http://www.opscode.com/chef/
.. _`Puppet`: http://puppetlabs.com/
.. _`Salt`: http://docs.saltstack.com/topics/
.. _`CFEngine`: http://cfengine.com/
.. _`paramiko`: http://www.paramiko.org/
