import requests
import json

EC2_OFFERS={
0:	"EC2InstanceSavingsPlans 1 year No Upfront",
1:	"EC2InstanceSavingsPlans 1 year Partial Upfront",
2:	"ComputeSavingsPlans 1 year All Upfront",
3:	"ComputeSavingsPlans 3 year All Upfront",
4:	"EC2InstanceSavingsPlans 3 year All Upfront",
5:	"EC2InstanceSavingsPlans 3 year No Upfront",
6:	"ComputeSavingsPlans 3 year Partial Upfront",
7:	"ComputeSavingsPlans 1 year Partial Upfront",
8:	"EC2InstanceSavingsPlans 3 year Partial Upfront",
9:	"EC2InstanceSavingsPlans 1 year All Upfront",
10:	"ComputeSavingsPlans 3 year No Upfront",
11:	"ComputeSavingsPlans 1 year No Upfront",
12: "On Demand"
}

def ec2_price(instance_type, location, OS="Linux", offer_type="On Demand", disk=None):
    '''
    param offer_type: Can be on_demand, saving_plans, reserved 
                      or even All for a dict with the prices
    type  offer_type: `str`

    param OS: Maybe either "Linux" or "Windows"
    type  OS: `str`
    '''

    URL = ("https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/"
           "computesavingsplan/USD/current/compute-instance-savings"
           "-plan-ec2-calc/{}/{}/{}/NA/Shared/index.json").format(
               instance_type,location,OS
           )
    
    response = requests.get(URL)
    if response.status_code == 200:
        data = response.json()
    else:
        response.raise_for_status()
    prices={}
    for _, offer in EC2_OFFERS.items():
        if offer == "On Demand":
            prices[offer] = data['regions'][location][EC2_OFFERS[0]]['ec2:PricePerUnit']
            continue
        prices[offer] = data['regions'][location][offer]['price']
    
    if offer_type == "All":
        return prices
    return prices[offer_type]
    

if __name__ == "__main__":
    print(ec2_price("t3a.large", location="Asia Pacific (Tokyo)", offer_type="All"))