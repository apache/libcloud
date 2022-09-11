#!/usr/bin/env python
#
#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.
#
# Script which generates markdown formatted list of contributors. It generates
# this list by parsing the "CHANGES" file.
#
# Usage:
#
# 1. Generate a list of contributors with tickets for all versions:
#
# ./contrib/generate_contributor_list.py --changes-path=CHANGES.rst \
#                                         --include-tickets
#
# 2. Generate a list of contributors for a release without tickets
#
# ./contrib/generate_contributor_list.py --changes-path=CHANGES.rst \
#                                        --versions=0.13.0
# 3. Generate a list of contributors with tickets for multiple versions
#
# ./contrib/generate_contributor_list.py --changes-path=CHANGES.rst \
#                                         --include-tickets
#                                         --versions 0.11.0 0.12.0


import re
import argparse
from collections import defaultdict

JIRA_URL = "https://issues.apache.org/jira/browse/LIBCLOUD-%s"
GITHUB_URL = "https://github.com/apache/libcloud/pull/%s"


def parse_changes_file(file_path, versions=None):
    """
    Parse CHANGES file and return a dictionary with contributors.

    Dictionary maps contributor name to the JIRA tickets or Github pull
    requests the user has worked on.
    """
    # Maps contributor name to a list of JIRA tickets
    contributors_map = defaultdict(set)

    in_entry = False
    active_version = None
    active_tickets = []

    with open(file_path) as fp:
        for line in fp:
            line = line.strip()

            match = re.search(r"Changes with Apache Libcloud " r"(\d+\.\d+\.\d+(-\w+)?).*?$", line)

            if match:
                active_version = match.groups()[0]

            if versions and active_version not in versions:
                continue

            if line.startswith("-") or line.startswith("*)"):
                in_entry = True
                active_tickets = []

            if in_entry and line == "":
                in_entry = False

            if in_entry:
                match = re.search(r"\((.+?)\)$", line)

                if match:
                    active_tickets = match.groups()[0]
                    active_tickets = active_tickets.split(", ")
                    active_tickets = [
                        ticket
                        for ticket in active_tickets
                        if ticket.startswith("LIBCLOUD-") or ticket.startswith("GITHUB-")
                    ]

                match = re.search(r"^\[(.+?)\]$", line)

                if match:
                    contributors = match.groups()[0]
                    contributors = contributors.split(",")
                    contributors = [name.strip() for name in contributors]

                    for name in contributors:
                        name = name.title()
                        contributors_map[name].update(set(active_tickets))

    return contributors_map


def convert_to_markdown(contributors_map, include_tickets=False):

    # Contributors are sorted in ascending lexiographical order based on their
    # last name
    def compare(item1, item2):
        lastname1 = item1.split(" ")[-1].lower()
        lastname2 = item2.split(" ")[-1].lower()
        return (lastname1 > lastname2) - (lastname1 < lastname2)

    names = contributors_map.keys()
    names = sorted(names, cmp=compare)

    result = []
    for name in names:
        tickets = contributors_map[name]

        tickets_string = []

        for ticket in tickets:
            if "-" not in ticket:
                # Invalid ticket number
                continue

            number = ticket.split("-")[1]

            if ticket.startswith("LIBCLOUD-"):
                url = JIRA_URL % (number)
            elif ticket.startswith("GITHUB-") or ticket.startswith("GH-"):
                url = GITHUB_URL % (number)

            values = {"ticket": ticket, "url": url}
            tickets_string.append("[%(ticket)s](%(url)s)" % values)

        tickets_string = ", ".join(tickets_string)

        if include_tickets:
            line = "* {name}: {tickets}".format(name=name, tickets=tickets_string)
        else:
            line = "* {name}".format(name=name)

        result.append(line.strip())

    result = "\n".join(result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assemble provider logos " " in a single image")
    parser.add_argument(
        "--changes-path", action="store", required=True, help="Path to the changes file"
    )
    parser.add_argument(
        "--versions",
        action="store",
        nargs="+",
        type=str,
        help="Only return contributors for the provided " "versions",
    )
    parser.add_argument(
        "--include-tickets",
        action="store_true",
        default=False,
        help="Include ticket numbers",
    )
    args = parser.parse_args()

    contributors_map = parse_changes_file(file_path=args.changes_path, versions=args.versions)
    markdown = convert_to_markdown(
        contributors_map=contributors_map, include_tickets=args.include_tickets
    )

    print(markdown)
