"""This module defines a Pulumi component resource for encapsulating our best practices for building an AWS VPC.

This includes:
- TODO Create the named VPC with appropriate tags
- TODO Create a minimum of 3 subnets across multiple availability zones
- TODO Create an internet gateway
- TODO Create an IPv6 egress gateway (Why??)
- TODO  Create a route table and associate the created subnets with it
- TODO Create a routing table to include the relevant peers and their networks
- TODO Create an RDS subnet group (Why??)
"""
from pulumi import ComponentResource, Config
from pulumi_aws import ec2, get_availability_zones

# TODO Vpc Component
class Vpc(ComponentResource):
    """Pulumi component for building all of the necessary pieces of an AWS VPC.

    A component resource that encapsulates all of the standard practices of how the Dicey Tech
     Engineering team constructs and organizes VPC environments in AWS.
    """

    def __init__(self, az_count):
        """
        Build an AWS VPC with subnets, internet gateway, and routing table.

        :param vpc_config: Configuration object for customizing the created VPC and
            associated resources.
        :type vpc_config: OLVPCConfig
        :param opts: Optional resource options to be merged into the defaults.  Useful
            for handling things like AWS provider overrides.
        :type opts: Optional[ResourceOptions]
        """
        super().__init__("educate:infrastruture:aws:VPC", "educate-app-vpc")

        self.tags = {"pulumi_managed": "true", "AutoOff": "True"}

        self.vpc = ec2.Vpc("educate-app-vpc", cidr_block="10.0.0.0/16")

        self.igw = ec2.InternetGateway("educate-app-igw", vpc_id=self.vpc.id)

        self.public_route_table = ec2.RouteTable(
            "educate-app-rt",
            routes=[
                ec2.RouteTableRouteArgs(cidr_block="0.0.0.0/0", gateway_id=self.igw.id)
            ],
            vpc_id=self.vpc.id,
        )

        self.public_subnet_ids = []

        # config = Config("apps_vpc")
        # az_count = config.require_int("az_count")
        zones = get_availability_zones().names[:az_count]

        # TODO make subnet cird programmatically defined
        for zone in zones:
            # TODO Create 1 public and 1 private subnet
            public_subnet = ec2.Subnet(
                f"educate-public-subnet-{zone}",
                assign_ipv6_address_on_creation=False,
                vpc_id=self.vpc.id,
                map_public_ip_on_launch=True,
                cidr_block="10.0.1.0/24",
                availability_zone=zone,
                tags=self.tags,
            )

            ec2.RouteTableAssociation(
                f"educate-app-public-rta-{zone}",
                route_table_id=self.public_route_table.id,
                subnet_id=public_subnet.id,
            )

            self.public_subnet_ids.append(public_subnet.id)

    def get_id(self):
        return self.vpc.id

    def get_public_subnet_id(self):
        return self.public_subnet_ids[0]


#apps_vpc = Vpc(1)