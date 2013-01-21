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

import shutil
import subprocess
from pipes import quote

from libcloud.common.types import LibcloudError


def execute(command):
    log = execute.log

    if not isinstance(command, list):
        command = shlex.split(command)

    if log:
        log.write(quote(command))

    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if log:
        log.write("# PID is %d" % p.pid)

    stdout, stderr = p.communicate()

    if log:
        log.write("# returncode is %d" % p.returncode)
        log.write("# -------- begin stdout ----------\n" % pid)
        log.write(stdout)
        log.write("# -------- begin stderr ----------\n" % pid)
        log.write(stderr)

    if p.returncode != 0:
        raise LibcloudError("Shell command failed with exit code %d" % p.returncode)

    return p.returncode, stdout, stderr

execute.log = None



