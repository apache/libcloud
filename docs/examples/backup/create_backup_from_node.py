import time
from pprint import pprint

from libcloud.backup.types import Provider as BackupProvider
from libcloud.backup.types import BackupTargetJobStatusType
from libcloud.compute.types import Provider as ComputeProvider
from libcloud.backup.providers import get_driver as get_backup_driver
from libcloud.compute.providers import get_driver as get_compute_driver

backup_driver = get_backup_driver(BackupProvider.DIMENSIONDATA)("username", "api key")
compute_driver = get_compute_driver(ComputeProvider.DIMENSIONDATA)("username", "api key")

nodes = compute_driver.list_nodes()

# Backup the first node in the pool
selected_node = nodes[0]

print("Enabling backup for node")
new_target = backup_driver.create_target_from_node(selected_node)

print("Starting backup of node")
job = backup_driver.create_target_job(new_target)

print("Waiting for job to complete")
while True:
    if job.status != BackupTargetJobStatusType.RUNNING:
        break
    else:
        job = backup_driver.get_target_job(job.id)

    print("Job is now at %s percent complete" % (job.progress))
    time.sleep(20)

print("Job is completed with status- %s" % (job.status))

print("Getting a list of recovery points")
recovery_points = backup_driver.list_recovery_points(new_target)
pprint(recovery_points)
