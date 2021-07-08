"""Manage the creation of VPC infrastructure and the peering relationships between them.


"""
from ipaddress import IPv4Network
from pulumi import Config, export, get_stack

from educate_infrastructure.infra.network.vpc import (
    DTVpc,
    DTVPCConfig,
)

env = get_stack()

apps_config = Config("apps_vpc")
app_network = IPv4Network(apps_config.require("cidr_block"))
apps_network_config = DTVPCConfig(
    name="educate-app",
    cidr_block=app_network,
    rds_network=True,
)

apps_vpc = DTVpc(apps_network_config)

export("apps_vpc_id", apps_vpc.get_id())
export("apps_public_subnet_ids", apps_vpc.get_public_subnet_ids())
export("apps_private_subnet_ids", apps_vpc.get_private_subnet_ids())
export("db_subnet_group_name", apps_vpc.get_db_subnet_group_name())
