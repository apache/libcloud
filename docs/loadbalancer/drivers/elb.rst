Elastic Load Balancing interface for AWS
========================================

What is Elastic Load Balancing?
-------------------------------

Amazon Web Services (AWS) provides Elastic Load Balancing to automatically
distribute incoming web traffic across multiple Amazon Elastic Compute Cloud
(Amazon EC2) instances. With Elastic Load Balancing, you can add and remove
EC2 instances as your needs change without disrupting the overall flow of
information. If one EC2 instance fails, Elastic Load Balancing automatically
reroutes the traffic to the remaining running EC2 instances. If the failed
EC2 instance is restored, Elastic Load Balancing restores the traffic to
that instance. Elastic Load Balancing offers clients a single point of
contact, and it can also serve as the first line of defense against attacks
on your network. You can offload the work of encryption and decryption to
Elastic Load Balancing, so your servers can focus on their main task.


Ok Now Tell me some advantages of using Elastic Load Balancing
---------------------------------------------------------------

* Distribution of requests to Amazon EC2 instances (servers)in multiple
  vailability Zones so that the risk of overloading one single instance
  is minimized.
* Continuous monitoring of the health of Amazon EC2 instances registered
  with the load balancer.
* Support for end-to-end traffic encryption on those networks that use
  secure (HTTPS/SSL) connections.
* Support for the sticky session feature, which is the ability to "stick"
  user sessions to specific Amazon EC2 instances.
* Association of the load balancer with your domain name.
* Supports use of both the Internet Protocol version 4 (IPv4) and
  Internet Protocol version 6 (IPv6).

"How it works?" would be nice to share
--------------------------------------

Elastic Load Balancing consists of two components: the load balancers and
the controller service. The load balancers monitor the traffic and handle
requests that come in through the Internet. The controller service monitors
the load balancers, adding and removing load balancers as needed and
verifying that the load balancers are functioning properly.

* The client sends a URL request to DNS servers to access your application.
  For example, myLB-1234567890.us-east-1.elb.amazonaws.com.
* Then The client looks for the resolution of the DNS name sent by the
  DNS server.
* The client then opens a connection to the machine at the provided IP address.
  The instance at this address is the load balancer you created.
* The load balancer checks the health states of all the registered EC2 application
  instances within the selected Availability Zones
* Then load balancer routes the client request to the healthy EC2 application
  instance identified in the previous step.

That's not enough, you want to learn more about ELB, then Refer `AWS site
<http://docs.aws.amazon.com/ElasticLoadBalancing/latest/APIReference/Welcome.html/>`_.


Now lets dive into the tutorial which will focus on libcloud Elastic
Load Balancing interface for AWS.

1. Creating a Connection
-------------------------

The first step in accessing ELB is to create a connection to the service.

So, when you instantiate an ELB driver you need to pass the following arguments
to the driver constructor:

* ``key`` - Your AWS API key
* ``secret`` - Your AWS secret key
* ``region`` - The region of your AWS instance host point
  (e.g ``us-west-2`` for ``US West (Oregon) Region``)

Typically this will lead to:

.. literalinclude:: /examples/loadbalancer/elb/create_lb_connection_for_aws.py
   :language: python

if everything gone well; means if your console has not yelled any error then
your connection has been established.

by the way if you have difficulty in getting your 'access key' and 'secret key'
id's, look at security credentials page of AWS management console.


The base `libcloud` ELB API allows you to:

* list, create, attach, detach, delete load balancer
* list protocols related to load balancer

Non-standard functionality and extension methods
-------------------------------------------------

The AWS ELB driver exposes a lot of `libcloud` non-standard
functionalities through extension methods and arguments.

These functionalities include:

* list laod balancer policy
* list load balancer policy types
* create, delete load balancer policy
* create listeners for load balancer
* enable/disable policies on backend server & listeners

2. Getting Existing Load Balancers
-----------------------------------

To retrieve any exiting load balancers available

.. literalinclude:: /examples/loadbalancer/elb/list_load_balancer.py
   :language: python

this will return you a list of load balancers
``[<LoadBalancer: id=balancer_id, name=balancer_name, state=balancer_state>]``

3. Creating New Load Balancers
-------------------------------

To create new load balancer initialise some members for the load balancer
first

.. literalinclude:: /examples/loadbalancer/elb/create_load_balancer.py
   :language: python

Ok if everything is fine; you will see this on your python shell screen
``[<LoadBalancer: id='MyLB', name='MyLB', state=1]``

note: ``state`` value may differ

4. Creating Load Balancer Policy
--------------------------------

To creates a new policy for a load balancer that contains the necessary
attributes depending on the policy type

.. literalinclude:: /examples/loadbalancer/elb/create_lb_policy.py
   :language: python

If you get ``True``, then congratulation you have successfully created
the load balancer policy.

Now there are some extension methods to look on
To get all policy associated with the load balancer

.. literalinclude:: /examples/loadbalancer/elb/ex_list_balancer_policies.py
   :language: python

you will get output something like this
 ``['EnableProxyProtocol']``

To get all the policy types available

.. literalinclude:: /examples/loadbalancer/elb/ex_list_balancer_policy_types.py
   :language: python

It will return a list of available policy types
 ``['EnableProxyProtocolType']``

To delete a policy associated with the load balancer

.. literalinclude:: /examples/loadbalancer/elb/ex_delete_balancer_policy.py
   :language: python

Will return ``True`` if it deletes the policy successfully.

5. Enable/Disable Policy on Backend server
-------------------------------------------

Wait! first tell me about Policies
----------------------------------

A security policy is a combination of SSL Protocols, SSL Ciphers, and
the Server Order Preference option. For more information about
configuring SSL connection for your load balancer

Two Types

* Predefined Security Policy—A list of predefined SSL negotiation
  configurations with enabled ciphers and protocols
* Custom Security Policy—A list of ciphers and protocols that you
  specify to create a custom negotiation configuration

To enable the policies on the server we need to call
"SetLoadBalancerPoliciesForBackendServer" action.

.. literalinclude:: /examples/loadbalancer/elb/ex_set_balancer_policies_backend_server.py
   :language: python

Will return ``True`` if it sets the policies successfully on backend server.

To disable the policy you just need to pass the policies parameter as empty
list

6. Enable/Diable Policy on Listeners
-------------------------------------

I don't have any idea about ``listeners``?
------------------------------------------

A listener is a process that listens for connection requests.
It is configured with a protocol and a port number for front-end
(client to load balancer) and back-end (load balancer to back-end instance)
connections.

Elastic Load Balancing supports the load balancing of applications
using HTTP, HTTPS (secure HTTP), TCP, and SSL (secure TCP) protocols.
The HTTPS uses the SSL protocol to establish secure connections over
the HTTP layer. You can also use SSL protocol to establish secure
connections over the TCP layer.

To create one or more listeners on a load balancer for the specified port

.. literalinclude:: /examples/loadbalancer/elb/ex_create_balancer_listeners.py
   :language: python

Will return ``True`` if it creates load balancer listeners successfully.

As mentioned above for backend Server, to enable the policies on the listeners,
need to call ``SetLoadBalancerPoliciesOfListener`` action

.. literalinclude:: /examples/loadbalancer/elb/ex_set_balancer_policies_listener.py
   :language: python

Will return ``True`` if it sets load balancer policies for listeners successfully.

To disable the policy you just need to pass the policies parameter as empty
list

Wrapping up
-----------

So now we have come to the end of tutorial. This last program file implements all
the above attributes of ELB driver that we have discussed.

.. literalinclude:: /examples/loadbalancer/elb/complete_tut.py
   :language: python
