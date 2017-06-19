Joyent Triton Container Driver Documentation
============================================

`Joyent Triton`_ is a Docker hosting service, provided by service provider Joyent.
Docker-native tools and elastic hosts make deploying on Triton as easy as running Docker on your laptop.
There is no special software to install or configure.
Mix Docker containers with container-native Linux to extend the benefits of containerization to legacy applications and stateful services.

.. figure:: /_static/images/provider_logos/triton.png
    :align: center
    :width: 300
    :target: http://joyent.com/

Instantiating the driver
------------------------

Download the script::

    curl -O https://raw.githubusercontent.com/joyent/sdc-docker/master/tools/sdc-docker-setup.sh
    
Now execute the script, substituting the correct values::

    bash sdc-docker-setup.sh <CLOUDAPI_URL> <ACCOUNT_USERNAME> ~/.ssh/<PRIVATE_KEY_FILE>

This should output something similar to the following::

    Setting up Docker client for SDC using:
        CloudAPI:        https://us-east-1.api.joyent.com
        Account:         jill
        Key:             /Users/localuser/.ssh/sdc-docker.id_rsa
    
    If you have a pass phrase on your key, the openssl command will
    prompt you for your pass phrase now and again later.
    
    Verifying CloudAPI access.
    CloudAPI access verified.
    
    Generating client certificate from SSH private key.
    writing RSA key
    Wrote certificate files to /Users/localuser/.sdc/docker/jill
    
    Get Docker host endpoint from cloudapi.
    Docker service endpoint is: tcp://us-east-1.docker.joyent.com:2376
    
    * * *
    Success. Set your environment as follows:
    
        export DOCKER_CERT_PATH=/Users/localuser/.sdc/docker/jill
        export DOCKER_HOST=tcp://us-east-1.docker.joyent.com:2376
        export DOCKER_CLIENT_TIMEOUT=300
        export DOCKER_TLS_VERIFY=1
        
.. literalinclude:: /examples/container/joyent/instantiate_driver.py
   :language: python
   
API Docs
--------

.. autoclass:: libcloud.container.drivers.joyent.JoyentContainerDriver
    :members:
    :inherited-members:


.. _`Joyent Triton`: https://www.joyent.com/blog/understanding-triton-containers
