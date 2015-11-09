# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__all__ = [
    'Provider',
    'BackupTargetType',
    'BackupTargetJobStatus'
]


class Provider(object):
    DUMMY = 'dummy'


class BackupTargetType(object):
    """
    Backup Target type.
    """

    """ Denotes a virtual host """
    VIRTUAL = 'Virtual'

    """ Denotes a physical host """
    PHYSICAL = 'Physical'

    """ Denotes a file system (e.g. NAS) """
    FILESYSTEM = 'Filesystem'

    """ Denotes a database target """
    DATABASE = 'Database'

    """ Denotes an object based file system """
    OBJECT = 'Object'


class BackupTargetJobStatus(object):
    """
    The status of a backup target job
    """

    RUNNING = 'Running'
    CANCELLED = 'Cancelled'
    FAILED = 'Failed'
    COMPLETED = 'Completed'
    PENDING = 'Pending'
