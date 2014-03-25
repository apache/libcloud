"""
Existing credentials are contained in the .gce_libcloud_auth file,
this file will have been created the first time you followed the
setup instructions.

To avoid using this static file on disk you can use the following
example code. Use this if you wish to store the tokens in a
database or use tokens for multiple accounts.

The token will be refreshed every 60 minutes using the
refresh_token. The new access_token will not be stored in
.gce_libcloud_auth.

To avoid using the .gce_libcloud_auth file, you can handle the
code exchange yourself. Once you have the code from visiting
the link provided when first setting up the driver. Use the code
from

https://github.com/apache/libcloud/blob/trunk/libcloud/common/google.py#L359
and
https://github.com/apache/libcloud/blob/trunk/libcloud/common/google.py#L297

Make the request to Google manually and store the details, the most important
is the refresh_token as this is used to refresh the access_token
after 60 minutes.

"""

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver


COMPUTE_ENGINE = get_driver(Provider.GCE)

CREDENTIALS = {
    "access_token": "ACCESS_TOKEN",
    "token_type": "Bearer",
    "expire_time": "2014-03-19T19:19:20Z",
    "expires_in": 3600,
    "refresh_token": "REFRESH_TOKEN"
}

# Create the DRIVER with the credentials directly so it won't access
# the .gce_libcloud_auth file.
DRIVER = COMPUTE_ENGINE('CLIENT_ID',
                        'CLIENT_SECRET',
                        project='PROJECT_NAME',
                        credential_file=CREDENTIALS)

print "Created DRIVER"

print "Listing zones:"
print DRIVER.list_locations()

# Example code to spin up a server
#print "Starting node"
#print DRIVER.create_node('name_of_server', 'n1-standard-2',
#                   'debian-7', location='us-central1-a')

print "Finished"
