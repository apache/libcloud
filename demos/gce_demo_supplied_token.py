"""
The access_token is contained in your existing .gce_libcloud_auth file
that file will have been created the first time you followed the
setup instructions.

The example below bypasses the need for this file.

The token will be refreshed every 60 minutes using the
refresh_token. The new access_token will not be stored in
.gce_libcloud_auth, it will only existing in the running
code.

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

print "Created driver"

print "Listing zones:"
print DRIVER.list_locations()

# Example code to spin up a server
#print "Starting node"
#print DRIVER.create_node('name_of_server', 'n1-standard-2',
#                   'debian-7', location='us-central1-a')

print "Finished"
