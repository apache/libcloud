from libcloud.loadbalancer.base import Member, Algorithm
from libcloud.loadbalancer.types import Provider
from libcloud.loadbalancer.providers import get_driver

ACCESS_ID = "your access id"
SECRET_KEY = "your secret key"


def main():
    cls = get_driver(Provider.ELB)
    driver = cls(key=ACCESS_ID, secret=SECRET_KEY)

    print(driver.list_balancers())

    # members associated with the load balancer
    members = (Member(None, "192.168.88.1", 8000), Member(None, "192.168.88.2", 8080))
    # creates a new balancer named 'MyLB'
    new_balancer = driver.create_balancer(
        name="MyLB",
        algorithm=Algorithm.ROUND_ROBIN,
        port=80,
        protocol="http",
        members=members,
    )
    print(new_balancer)

    # create load balancer policy
    print(
        driver.ex_create_balancer_policy(
            name="MyLB",
            policy_name="EnableProxyProtocol",
            policy_type="ProxyProtocolPolicyType",
            policy_attributes={"ProxyProtocol": "true"},
        )
    )

    # delete load balancer policy
    print(driver.ex_delete_balancer_policy(name="MyLB", policy_name="EnableProxyProtocol"))

    # set load balancer policies for backend server
    print(
        driver.ex_set_balancer_policies_backend_server(
            name="MyLB", port=80, policies=["MyDurationStickyPolicy"]
        )
    )

    # create the listeners for the balancers
    uid = "arn:aws:iam::123456789012:server-certificate/servercert"
    print(driver.ex_create_balancer_listeners(name="MyLB", listeners=[[1024, 65533, "HTTPS", uid]]))

    # set the listeners policies for the balancers
    print(
        driver.ex_set_balancer_policies_listener(
            name="MyLB", port=80, policies=["MyDurationStickyPolicy"]
        )
    )


if __name__ == "__main__":
    main()
