"""This module defines a Pulumi component resource for encapsulating our best practices for building an AWS VPC.

This includes:
- Create the named VPC with appropriate tags
- Create a public and private subnet for each select Availability Zones
- Create an internet gateway
- Create a route table and associate the created subnets with it
- Create a routing table to include the relevant peers and their networks
- Create an RDS subnet group
"""
from itertools import cycle
from typing import List, Text, Dict, Optional
from ipaddress import IPv4Network

from pulumi import ComponentResource, ResourceOptions, info
from pulumi_aws import ec2, get_availability_zones, rds
from pydantic import BaseModel, PositiveInt

SUBNET_PREFIX_V4 = (
    24  # A CIDR block of prefix length 24 allows for up to 255 individual IP addresses
)


class DTVPCConfig(BaseModel):
    """
    Configuration object for defining configuration needed to create a VPC.
    """

    name: Text
    az_count: Optional[PositiveInt] = 2
    cidr_block: IPv4Network
    rds_network: Optional[bool] = False

    class Config:
        arbitrary_types_allowed = True


class DTVpc(ComponentResource):
    """Pulumi component for building all of the necessary pieces of an AWS VPC.

    A component resource that encapsulates all of the standard practices of how the Dicey Tech
    Engineering team constructs and organizes VPC environments in AWS.
    """

    def __init__(self, network_config: DTVPCConfig, opts: ResourceOptions = None):
        """
        Build an AWS VPC with subnets, internet gateway, and routing table.

        :param network_config: Configuration object for customizing the created VPC and
            associated resources.
        :type vpc_config: DTVPCConfig

        :param opts: Optional resource options to be merged into the defaults.  Useful
            for handling things like AWS provider overrides.
        :type opts: Optional[ResourceOptions]

        """
        self.name = network_config.name
        self.rds_network = network_config.rds_network

        super().__init__("diceytech:infrastruture:aws:VPC", f"{self.name}-vpc", opts)

        self.tags = {"pulumi_managed": "true", "AutoOff": "False"}

        self.vpc = ec2.Vpc(
            f"{self.name}-vpc",
            cidr_block=str(network_config.cidr_block),
            assign_generated_ipv6_cidr_block=True,
            tags={**self.tags, "Name": self.name},
            opts=ResourceOptions(parent=self),
        )

        self.s3_gateway_endpoint = ec2.VpcEndpoint(
            f"{self.name}-s3-gateway-endpoint",
            vpc_id=self.vpc.id,
            service_name="com.amazonaws.eu-west-2.s3",
            opts=ResourceOptions(parent=self),
        )

        self.igw = ec2.InternetGateway(
            f"{self.name}-igw",
            vpc_id=self.vpc.id,
            opts=ResourceOptions(parent=self),
        )

        self.public_route_table = ec2.RouteTable(
            f"{self.name}-public-rt",
            routes=[
                ec2.RouteTableRouteArgs(cidr_block="0.0.0.0/0", gateway_id=self.igw.id)
            ],
            vpc_id=self.vpc.id,
            opts=ResourceOptions(parent=self),
        )

        self.public_subnet_ids: List[ec2.Subnet] = []
        self.nat_gateway_ids: Dict[Text, Text] = {}
        self.private_subnet_ids: List[ec2.Subnet] = []
        zones: List[Text] = get_availability_zones().names[: network_config.az_count]

        subnet_iterator = zip(
            range(network_config.az_count * 2),
            cycle(zones),
            network_config.cidr_block.subnets(new_prefix=SUBNET_PREFIX_V4),
        )

        if self.rds_network:
            for index, zone, subnet_v4 in subnet_iterator:
                if index < network_config.az_count:
                    self.create_subnet(zone, subnet_v4, is_public=False)

            self.db_subnet_group = rds.SubnetGroup(
                f"{self.name}-db-subnet-group",
                description=f"RDS subnet group for {self.name}",
                name=f"{self.name}-db-subnet-group",
                subnet_ids=[net_id for net_id in self.private_subnet_ids],
                tags=self.tags,
                opts=ResourceOptions(parent=self),
            )

            self.register_outputs(
                {
                    "public_subnet_ids": self.public_subnet_ids,
                    "private_subnet_ids": self.private_subnet_ids,
                    "db_subnet_group_name": self.db_subnet_group.name,
                }
            )
        else:
            for index, zone, subnet_v4 in subnet_iterator:
                if index < network_config.az_count:
                    self.create_subnet(zone, subnet_v4, is_public=True)
                else:
                    self.create_subnet(zone, subnet_v4, is_public=False)

            self.register_outputs(
                {
                    "public_subnet_ids": self.public_subnet_ids,
                    "private_subnet_ids": self.private_subnet_ids,
                }
            )

        info(msg=f"{self.name}-vpc created.", resource=self)

    def get_id(self) -> Text:
        return self.vpc.id

    def get_public_subnet_ids(self) -> List[Text]:
        return self.public_subnet_ids

    def get_private_subnet_ids(self) -> List[Text]:
        return self.private_subnet_ids

    def get_db_subnet_group_name(self) -> Text:
        if self.rds_network:
            return self.db_subnet_group.name

    def create_subnet(self, zone: Text, subnet_v4, is_public):
        if is_public:
            name_pre = f"{self.name}-public"
        else:
            name_pre = f"{self.name}-private"

        subnet = ec2.Subnet(
            f"{name_pre}-subnet-{zone}",
            assign_ipv6_address_on_creation=False,
            vpc_id=self.vpc.id,
            map_public_ip_on_launch=is_public,
            cidr_block=str(subnet_v4),
            availability_zone=zone,
            tags=self.tags,
            opts=ResourceOptions(parent=self),
        )

        if is_public:
            ec2.RouteTableAssociation(
                f"{name_pre}-rta-{zone}",
                route_table_id=self.public_route_table.id,
                subnet_id=subnet.id,
                opts=ResourceOptions(parent=self),
            )

            self.public_subnet_ids.append(subnet.id)

            if not self.rds_network:
                eip = ec2.Eip(
                    f"{self.name}-eip-{zone}",
                    tags=self.tags,
                    opts=ResourceOptions(parent=self),
                )

                nat_gateway = ec2.NatGateway(
                    f"{self.name}-natgw-{zone}",
                    subnet_id=subnet.id,
                    allocation_id=eip.id,
                    tags=self.tags,
                    opts=ResourceOptions(parent=self),
                )

                self.nat_gateway_ids[f"{zone}"] = nat_gateway.id
        else:
            if self.rds_network:
                private_rt = ec2.RouteTable(
                    f"{name_pre}-rt-{zone}",
                    vpc_id=self.vpc.id,
                    routes=[
                        ec2.RouteTableRouteArgs(
                            cidr_block="0.0.0.0/0",
                            # egress_only_gateway_id=self.egress_igw.id,
                            gateway_id=self.igw.id,
                        )
                    ],
                    tags=self.tags,
                    opts=ResourceOptions(parent=self),
                )
            else:
                private_rt = ec2.RouteTable(
                    f"{name_pre}-rt-{zone}",
                    vpc_id=self.vpc.id,
                    routes=[
                        ec2.RouteTableRouteArgs(
                            cidr_block="0.0.0.0/0",
                            gateway_id=self.nat_gateway_ids[f"{zone}"],
                        ),
                    ],
                    tags=self.tags,
                    opts=ResourceOptions(parent=self),
                )

            ec2.RouteTableAssociation(
                f"{name_pre}-rta-{zone}",
                route_table_id=private_rt.id,
                subnet_id=subnet.id,
                opts=ResourceOptions(parent=self),
            )

            self.private_subnet_ids.append(subnet.id)


class DTVPCPeeringConnection(ComponentResource):
    """A Pulumi component for creating a VPC peering connection and populating bidirectional routes."""

    def __init__(
        self,
        vpc_peer_name: Text,
        source_vpc: DTVpc,
        destination_vpc: DTVpc,
    ):
        """Create a peering connection and associated routes between two managed VPCs.
        :param vpc_peer_name: The name of the peering connection
        :type vpc_peer_name: Text
        :param source_vpc: The source VPC object to be used as one end of the peering
            connection.
        :type source_vpc: OLVPC
        :param destination_vpc: The destination VPC object to be used as the other end
            of the peering connection
        :type destination_vpc: OLVPC
        :param opts: Resource option definitions to propagate to the child resources
        :type opts: Optional[ResourceOptions]
        """
        super().__init__(
            "dt:infrastructure:aws:VPCPeeringConnection", vpc_peer_name, None
        )

        self.peering_connection = ec2.VpcPeeringConnection(
            f"{source_vpc.name}-to-{destination_vpc.name}-vpc-peer",
            auto_accept=True,
            vpc_id=source_vpc.vpc.id,
            peer_vpc_id=destination_vpc.vpc.id,
            tags={"pulumi_managed": "True"},
            opts=ResourceOptions(parent=self),
        )

        self.source_to_dest_route = ec2.Route(
            f"{source_vpc.name}-to-{destination_vpc.name}-route",
            route_table_id=source_vpc.public_route_table.id,
            destination_cidr_block=destination_vpc.vpc.cidr_block,
            vpc_peering_connection_id=self.peering_connection.id,
            opts=ResourceOptions(parent=self),
        )

        self.dest_to_source_route = ec2.Route(
            f"{destination_vpc.name}-to-{source_vpc.name}-route",
            route_table_id=destination_vpc.public_route_table.id,
            destination_cidr_block=source_vpc.vpc.cidr_block,
            vpc_peering_connection_id=self.peering_connection.id,
            opts=ResourceOptions(parent=self),
        )

        self.register_outputs({})
