"""Manage the creation of VPC infrastructure and the peering relationships between them.


"""

import pulumi
from pulumi_aws import GetAmiFilterArgs, ec2, get_ami, get_availability_zones

from vpc import DTVpc

apps_vpc = DTVpc(name="educate-app", az_count=2)

pulumi.export("vpc_id", apps_vpc.get_id())
pulumi.export("public_subnet_ids", apps_vpc.get_public_subnet_ids())
pulumi.export("public_private_ids", apps_vpc.get_private_subnet_ids())

# TODO Create a VPC for the databases

# TODO Peer both VPCs