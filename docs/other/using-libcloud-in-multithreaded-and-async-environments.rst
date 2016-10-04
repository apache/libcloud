Using Libcloud in multi-threaded and async environments
=======================================================

Libcloud's primary task is to communicate with different provider APIs using
HTTP. This means most of the work is not CPU intensive, but performing all
those HTTP requests includes a lot of waiting which makes the library I/O
bound.

Most of the time you want to perform more operations in parallel or just
want your code to finish faster (for example starting a lot of servers or
periodically polling for node status).

Problems like this are usually solved using threads or async libraries such
as Twisted, Tornado or gevent.

This page contains some information and tips about how to use Libcloud in
such environments.

Libcloud and thread-safety
--------------------------

Important thing to keep in mind when dealing with threads is thread-safety.
Libcloud driver instance is **not** thread safe. This means if you don't want
to deal with complex (and usually inefficient) locking the easiest solution
is to create a new driver instance inside each thread.

Using Libcloud with gevent
--------------------------

gevent has an ability to monkey patch and replace functions in the Python
``socket``, ``urllib2``, ``httplib`` and ``time`` module with its own
functions which don't block.

You need to do two things when you want to use Libcloud with gevent:

* Enable monkey patching

.. sourcecode:: python

    from gevent import monkey
    monkey.patch_all()

* Create a separate driver instance for each Greenlet. This is necessary
  because a driver instance reuses the same Connection class.

For an example see :doc:`Efficiently download multiple files using gevent </storage/examples>`.

Using Libcloud with Twisted
---------------------------

Libcloud has no Twisted support included in the core which means you need
to be careful when you use it with Twisted and some other async frameworks.

If you don't use it properly it can block the whole reactor (similar as
any other blocking library or a long CPU-intensive task) which means the
execution of other pending tasks in the event queue will be blocked.

A simple solution to prevent blocking the reactor is to run Libcloud
calls inside a thread. In Twisted this can be achieved using
``threads.deferToThread`` which runs a provided method inside the Twisted
thread pool.

The example below demonstrates how to create a new node inside a thread
without blocking the whole reactor.

.. literalinclude:: /examples/misc/twisted_create_node.py
   :language: python


