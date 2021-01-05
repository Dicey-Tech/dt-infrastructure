"""Manage the creation of VPC infrastructure and the peering relationships between them.


"""
from ipaddress import IPv4Network
from pulumi import Config, export
from pulumi_aws import GetAmiFilterArgs, ec2, get_ami, get_availability_zones

from vpc import DTVpc

apps_config = Config("apps_vpc")
app_network = IPv4Network(apps_config.require("cidr_block"))
apps_vpc = DTVpc(name="educate-app", az_count=2, cidr_block=app_network)


# TODO Create a VPC for the databases
db_config = Config("db_vpc")
db_network = IPv4Network(db_config.require("cidr_block"))
databases_vpc = DTVpc(name="databases", az_count=1, cidr_block=db_network)

# TODO Peer both VPCs

export("apps_vpc_id", apps_vpc.get_id())
export("apps_public_subnet_ids", apps_vpc.get_public_subnet_ids())
export("apps_private_subnet_ids", apps_vpc.get_private_subnet_ids())

export("db_vpc_id", databases_vpc.get_id())
export("db_public_subnet_ids", databases_vpc.get_public_subnet_ids())
export("db_private_subnet_ids", databases_vpc.get_private_subnet_ids())