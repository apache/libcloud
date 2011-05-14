#!/usr/bin/env python

import os
import time

from libcloud.loadbalancer.base import LB, LBMember
from libcloud.loadbalancer.types import Provider, LBState
from libcloud.loadbalancer.providers import get_driver

def main():
    Rackspace = get_driver(Provider.RACKSPACE)

    driver = Rackspace('username', 'api key')

    balancers = driver.list_balancers()

    # creating a balancer which balances traffic across two
    # nodes: 192.168.86.1:80 and 192.168.86.2:8080. Balancer
    # itself listens on port 80/tcp
    new_balancer_name = 'testlb' + os.urandom(4).encode('hex')
    new_balancer = driver.create_balancer(name=new_balancer_name,
            port=80,
            nodes=(LBMember(None, '192.168.86.1', 80),
                LBMember(None, '192.168.86.2', 8080))
            )

    print new_balancer

    # wait for balancer to become ready
    # NOTE: in real life code add timeout to not end up in
    # endless loop when things go wrong on provider side
    while True:
        balancer = driver.balancer_detail(balancer=new_balancer)

        if balancer.state == LBState.RUNNING:
            break

        time.sleep(30)

    # fetch list of nodes
    nodes = balancer.list_nodes()
    print nodes

    # remove first node
    balancer.detach_node(nodes[0])

    # and add another one: 10.0.0.10:1000
    print balancer.attach_node(ip='10.0.0.10', port='1000')

    # remove the balancer
    driver.destroy_balancer(new_balancer)

if __name__ == "__main__":
    main()
