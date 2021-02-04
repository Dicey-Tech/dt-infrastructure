"""Manage the creation of VPC infrastructure and the peering relationships between them.


"""
from ipaddress import IPv4Network
from pulumi import Config, export, get_stack

from educate_infrastructure.infra.network.vpc import (
    DTVpc,
    DTVPCPeeringConnection,
    DTVPCConfig,
)

env = get_stack()

apps_config = Config("apps_vpc")
app_network = IPv4Network(apps_config.require("cidr_block"))
apps_network_config = DTVPCConfig(
    name="educate-app",
    cidr_block=app_network,
)

apps_vpc = DTVpc(apps_network_config)

db_config = Config("db_vpc")
db_network = IPv4Network(db_config.require("cidr_block"))
db_network_config = DTVPCConfig(
    name="databases",
    cidr_block=db_network,
    rds_network=True,
)

databases_vpc = DTVpc(db_network_config)

apps_to_db_peer = DTVPCPeeringConnection(
    f"dt-apps-{env}-to-db-{env}-vpc-peer",
    apps_vpc,
    databases_vpc,
)

export("apps_vpc_id", apps_vpc.get_id())
export("apps_public_subnet_ids", apps_vpc.get_public_subnet_ids())
export("apps_private_subnet_ids", apps_vpc.get_private_subnet_ids())

export("db_vpc_id", databases_vpc.get_id())
export("db_public_subnet_ids", databases_vpc.get_public_subnet_ids())
export("db_private_subnet_ids", databases_vpc.get_private_subnet_ids())
export("db_subnet_group_name", databases_vpc.get_db_subnet_group_name())
