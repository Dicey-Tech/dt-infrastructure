"""This module defines a Pulumi component resource for encapsulating our best practices for building an AWS VPC.

This includes:
- Create the named VPC with appropriate tags
- Create a public and private subnet for each select Availability Zones
- Create an internet gateway
- Create a route table and associate the created subnets with it
- Create a routing table to include the relevant peers and their networks
"""
from itertools import cycle
from typing import List, Text, Dict

from pulumi import ComponentResource
from pulumi_aws import ec2, get_availability_zones

SUBNET_PREFIX_V4 = (
    24  # A CIDR block of prefix length 24 allows for up to 255 individual IP addresses
)


class DTVpc(ComponentResource):
    """Pulumi component for building all of the necessary pieces of an AWS VPC.

    A component resource that encapsulates all of the standard practices of how the Dicey Tech
     Engineering team constructs and organizes VPC environments in AWS.
    """

    def __init__(self, name: str, az_count: int, cidr_block):
        """
        Build an AWS VPC with subnets, internet gateway, and routing table.

        :param vpc_config: Configuration object for customizing the created VPC and
            associated resources.
        :type vpc_config: OLVPCConfig

        :param opts: Optional resource options to be merged into the defaults.  Useful
            for handling things like AWS provider overrides.
        :type opts: Optional[ResourceOptions]

        :param opts: Optional resource options to be merged into the defaults.  Useful
            for handling things like AWS provider overrides.
        :type opts: IPv4Network

        """
        self.name = name
        super().__init__("diceytech:infrastruture:aws:VPC", f"{self.name}-vpc")

        self.tags = {"pulumi_managed": "true", "AutoOff": "False"}
        self.vpc = ec2.Vpc(
            f"{self.name}-vpc", cidr_block=str(cidr_block), tags=self.tags
        )

        self.igw = ec2.InternetGateway(f"{self.name}-igw", vpc_id=self.vpc.id)

        self.public_route_table = ec2.RouteTable(
            f"{self.name}-public-rt",
            routes=[
                ec2.RouteTableRouteArgs(cidr_block="0.0.0.0/0", gateway_id=self.igw.id)
            ],
            vpc_id=self.vpc.id,
        )

        self.public_subnet_ids: List[ec2.Subnet] = []
        self.nat_gateway_ids: Dict[Text, Text] = {}
        self.private_subnet_ids: List[ec2.Subnet] = []
        zones: List[Text] = get_availability_zones().names[:az_count]

        # TODO make subnet cird programmatically defined
        subnet_iterator = zip(
            range(az_count * 2),
            cycle(zones),
            cidr_block.subnets(new_prefix=SUBNET_PREFIX_V4),
        )

        for index, zone, subnet_v4 in subnet_iterator:
            if index < az_count:
                self.create_subnet(index, zone, subnet_v4, is_public=True)
            else:
                self.create_subnet(index, zone, subnet_v4, is_public=False)

    def get_id(self):
        return self.vpc.id

    def get_public_subnet_ids(self):
        return self.public_subnet_ids

    def get_private_subnet_ids(self):
        return self.private_subnet_ids

    def create_subnet(self, index: int, zone: Text, subnet_v4, is_public):
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
        )

        if is_public:
            ec2.RouteTableAssociation(
                f"{name_pre}-rta-{zone}",
                route_table_id=self.public_route_table.id,
                subnet_id=subnet.id,
            )

            eip = ec2.Eip(f"{self.name}-eip-{zone}", tags=self.tags)
            nat_gateway = ec2.NatGateway(
                f"{self.name}-natgw-{zone}",
                subnet_id=subnet.id,
                allocation_id=eip.id,
                tags=self.tags,
            )

            self.nat_gateway_ids[f"{zone}"] = nat_gateway.id
            self.public_subnet_ids.append(subnet.id)
        else:
            # TODO Is 1 NAT Gateway per private subnet required?
            private_rt = ec2.RouteTable(
                f"{name_pre}-rt-{zone}",
                vpc_id=self.vpc.id,
                routes=[
                    {
                        "cidr_block": "0.0.0.0/0",
                        "gateway_id": self.nat_gateway_ids[f"{zone}"],
                    }
                ],
                tags=self.tags,
            )

            ec2.RouteTableAssociation(
                f"{name_pre}-rta-{zone}",
                route_table_id=private_rt.id,
                subnet_id=subnet.id,
            )

            self.private_subnet_ids.append(subnet.id)


# TODO Create a VPCConfig class to validate config values
# https://github.com/mitodl/ol-infrastructure/blob/87021e2a8681c769354c1b227328433adaa1af15/src/ol_infrastructure/components/aws/olvpc.py#L41


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
        )
        self.source_to_dest_route = ec2.Route(
            f"{source_vpc.name}-to-{destination_vpc.name}-route",
            route_table_id=source_vpc.public_route_table.id,
            destination_cidr_block=destination_vpc.vpc.cidr_block,
            vpc_peering_connection_id=self.peering_connection.id,
        )
        self.dest_to_source_route = ec2.Route(
            f"{destination_vpc.name}-to-{source_vpc.name}-route",
            route_table_id=destination_vpc.public_route_table.id,
            destination_cidr_block=source_vpc.vpc.cidr_block,
            vpc_peering_connection_id=self.peering_connection.id,
        )
        self.register_outputs({})