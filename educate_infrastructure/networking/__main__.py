"""Manage the creation of VPC infrastructure and the peering relationships between them.


"""

import pulumi
from pulumi_aws import GetAmiFilterArgs, ec2, get_ami, get_availability_zones

from vpc import Vpc

apps_vpc = Vpc(name="educate-app", az_count=1)

pulumi.export("vpc_id", apps_vpc.get_id())
pulumi.export("public_subnet_ids", apps_vpc.get_public_subnet_id())
pulumi.export("public_private_ids", apps_vpc.get_private_subnet_id())

# TODO Create a VPC for the databases

# TODO Peer both VPCs