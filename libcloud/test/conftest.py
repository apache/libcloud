import os.path
import pytest


def pytest_configure(config):
    """Check that secrets.py is valid"""

    this_dir = os.path.abspath(os.path.split(__file__)[0])
    secrets_current = os.path.join(this_dir, 'secrets.py')
    secrets_dist = os.path.join(this_dir, 'secrets.py-dist')

    if not os.path.isfile(secrets_current):
        print("Missing " + secrets_current)
        print("Maybe you forgot to copy it from -dist:")
        print("cp libcloud/test/secrets.py-dist libcloud/test/secrets.py")
        pytest.exit('')

    mtime_current = os.path.getmtime(secrets_current)
    mtime_dist = os.path.getmtime(secrets_dist)

    if mtime_dist > mtime_current:
        print("It looks like test/secrets.py file is out of date.")
        print("Please copy the new secrets.py-dist file over otherwise" +
              " tests might fail")
        pytest.exit('')
