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


class Provider(object):
    """
    Defines for each of the supported providers

    :cvar AWS_AUTOSCALE: Amazon AutoScale
    :cvar: AWS_CLOUDWATCH: Amazon CloudWatch
    :cvar SOFTLAYER: Softlayer
    """
    AWS_AUTOSCALE = 'aws_autoscale'
    AWS_CLOUDWATCH = 'aws_cloudwatch'
    SOFTLAYER = 'softlayer'


class AutoScaleAdjustmentType(object):
    """
    The logic to be used to scale the group when its policy is executed.

    :cvar CHANGE_IN_CAPACITY: Increases or decreases the existing capacity.
    :cvar EXACT_CAPACITY: Changes the current capacity to the specified value.
    :cvar PERCENT_CHANGE_IN_CAPACITY: Increases or decreases the capacity by a
                                      percentage.
    """

    CHANGE_IN_CAPACITY = 'CHANGE_IN_CAPACITY'
    EXACT_CAPACITY = 'EXACT_CAPACITY'
    PERCENT_CHANGE_IN_CAPACITY = 'PERCENT_CHANGE_IN_CAPACITY'


class AutoScaleTerminationPolicy(object):
    """
    The policy to be used for automatic removal of members from an auto scale
    group. Policy determines which members are chosen first for removal.

    :cvar OLDEST_INSTANCE: Terminates the oldest instance in the group.
    :cvar NEWEST_INSTANCE: Terminates the newest instance in the group.
    :cvar CLOSEST_TO_NEXT_CHARGE: Terminates instances that are closest to the
    next billing charge.
    :cvar DEFAULT: Default termination policy.

    """
    OLDEST_INSTANCE = 0
    NEWEST_INSTANCE = 1
    CLOSEST_TO_NEXT_CHARGE = 2
    DEFAULT = 3


class AutoScaleOperator(object):
    """
    The arithmetic operation to use when comparing the statistic
    and threshold.

    :cvar LT: Less than.
    :cvar LE: Less equals.
    :cvar GT: Greater than.
    :cvar GE: Great equals.

    """

    LT = 'LT'
    LE = 'LE'
    GT = 'GT'
    GE = 'GE'


class AutoScaleMetric(object):
    """
    :cvar CPU_UTIL: The percent CPU a guest is using.
    """
    CPU_UTIL = 'CPU_UTIL'
