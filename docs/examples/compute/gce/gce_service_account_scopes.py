# See previous examples for connecting and creating the driver
# ...
driver = None

# Define common example attributes
s = 'n1-standard-1'
i = 'debian-7'
z = 'us-central1-a'

# Service Account Scopes require a list of dictionaries. Each dictionary
# can have an optional 'email' address specifying the Service Account
# address, and list of 'scopes'. The default Service Account Scopes for
# new nodes will effectively use:

sa_scopes = [
    {
        'email': 'default',
        'scopes': ['storage-ro']
    }
]

# The expected scenario will likely use the default Service Account email
# address, but allow users to override the default list of scopes.
# For example, create a new node with full access to Google Cloud Storage
# and Google Compute Engine:
sa_scopes = [{'scopes': ['compute', 'storage-full']}]
node_1 = driver.create_node("n1", s, i, z, ex_service_accounts=sa_scopes)

# See Google's documentation for Accessing other Google Cloud services from
# your Google Compute Engine instances at,
# https://cloud.google.com/compute/docs/authentication
