.. note::

  Libcloud depends on the ``requests`` library for performing HTTP(s) requests.

  Prior to ``requests`` v2.26.0, ``requests`` depended on ``chardet`` library
  which is licensed under LGPL (requests library itself is licensed under the
  Apache License 2.0 license).

  Since Libcloud is not an application, but a library which is usually used
  along many other libraries in the same (virtual) environment, we can't have
  a strict dependency on requests >= 2.26.0 since that would break a lot of
  installations where users already depend on and have an older version of
  requests installed.

  If you are using requests < 2.26.0 along the Libcloud library you are using
  version of chardet library (chardet is a direct dependency of the requests
  library) which license is not compatible with Apache Libcloud.

  If using a LGPL dependency is a problem for your application, you should
  ensure you are using requests >= 2.26.0.

  It's also worth noting that Apache Libcloud doesn't bundle any 3rd party
  dependencies with our release artifacts - we only provide source code
  artifacts on our website.

  When installing Libcloud from PyPi using pip, pip will also download and use
  the latest version of requests without the problematic chardet dependency,
  unless you already have older version of the requests library installed in
  the same environment where you also want to use Libcloud - in that case,
  Libcloud will use the dependency which is already available and installed.
