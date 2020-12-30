"""This module defines a Pulumi component resource for encapsulating our best practices for building an AWS VPC.

This includes:
- Create the named VPC with appropriate tags
- TODO Create a minimum of 3 subnets across multiple availability zones
- TODO Create an internet gateway
- TODO Create an IPv6 egress gateway (Why??)
- TODO  Create a route table and associate the created subnets with it
- TODO Create a routing table to include the relevant peers and their networks
- TODO Create an RDS subnet group (Why??)
"""
from pulumi import ComponentResource
from pulumi_aws import ec2, get_availability_zones


class DTVpc(ComponentResource):
    """Pulumi component for building all of the necessary pieces of an AWS VPC.

    A component resource that encapsulates all of the standard practices of how the Dicey Tech
     Engineering team constructs and organizes VPC environments in AWS.
    """

    def __init__(self, name: str, az_count: int):
        """
        Build an AWS VPC with subnets, internet gateway, and routing table.

        :param vpc_config: Configuration object for customizing the created VPC and
            associated resources.
        :type vpc_config: OLVPCConfig
        :param opts: Optional resource options to be merged into the defaults.  Useful
            for handling things like AWS provider overrides.
        :type opts: Optional[ResourceOptions]
        """
        self.name = name
        super().__init__("diceytech:infrastruture:aws:VPC", f"{self.name}-vpc")

        self.tags = {"pulumi_managed": "true", "AutoOff": "False"}
        self.vpc = ec2.Vpc(f"{self.name}-vpc", cidr_block="10.0.0.0/16", tags=self.tags)

        self.igw = ec2.InternetGateway(f"{self.name}-igw", vpc_id=self.vpc.id)

        self.public_route_table = ec2.RouteTable(
            f"{self.name}-publi-rt",
            routes=[
                ec2.RouteTableRouteArgs(cidr_block="0.0.0.0/0", gateway_id=self.igw.id)
            ],
            vpc_id=self.vpc.id,
        )

        self.private_route_table = ec2.RouteTable(
            f"{self.name}-private-rt",
            routes=[
                ec2.RouteTableRouteArgs(cidr_block="0.0.0.0/0", gateway_id=self.igw.id)
            ],
            vpc_id=self.vpc.id,
        )

        self.public_subnet_ids = []
        self.private_subnet_ids = []
        zones = get_availability_zones().names[:az_count]

        # TODO make subnet cird programmatically defined
        public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
        private_subnet_cidrs = ["10.0.10.0/24", "10.0.11.0/24"]

        for zone, public_subnet_cidr, private_subnet_cidr in zip(
            zones, public_subnet_cidrs, private_subnet_cidrs
        ):
            self.create_subnet_pair(
                zone,
                public_subnet_cidr,
                private_subnet_cidr,
            )

    def get_id(self):
        return self.vpc.id

    def get_public_subnet_ids(self):
        return self.public_subnet_ids

    def get_private_subnet_ids(self):
        return self.private_subnet_ids

    def create_subnet_pair(
        self, zone: str, public_subnet_cidr: str, private_subnet_cidr: str
    ):
        public_subnet = ec2.Subnet(
            f"{self.name}-public-subnet-{zone}",
            assign_ipv6_address_on_creation=False,
            vpc_id=self.vpc.id,
            map_public_ip_on_launch=True,
            cidr_block=public_subnet_cidr,
            availability_zone=zone,
            tags=self.tags,
        )

        ec2.RouteTableAssociation(
            f"{self.name}-public-rta-{zone}",
            route_table_id=self.public_route_table.id,
            subnet_id=public_subnet.id,
        )

        self.public_subnet_ids.append(public_subnet.id)

        private_subnet = ec2.Subnet(
            f"{self.name}-private-subnet-{zone}",
            assign_ipv6_address_on_creation=False,
            vpc_id=self.vpc.id,
            map_public_ip_on_launch=False,
            cidr_block=private_subnet_cidr,
            availability_zone=zone,
            tags=self.tags,
        )

        eip = ec2.Eip(f"{self.name}-eip-{zone}", tags=self.tags)
        nat_gateway = ec2.NatGateway(
            f"{self.name}-natgw-{zone}",
            subnet_id=public_subnet.id,
            allocation_id=eip.id,
            tags=self.tags,
        )

        private_rt = ec2.RouteTable(
            f"pulumi-private-rt-{zone}",
            vpc_id=self.vpc.id,
            routes=[{"cidr_block": "0.0.0.0/0", "gateway_id": nat_gateway.id}],
            tags=self.tags,
        )

        ec2.RouteTableAssociation(
            f"{self.name}-private-rta-{zone}",
            route_table_id=private_rt.id,
            subnet_id=private_subnet.id,
        )

        self.private_subnet_ids.append(private_subnet.id)
