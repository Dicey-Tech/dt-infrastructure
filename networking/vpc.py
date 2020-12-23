"""This module defines a Pulumi component resource for encapsulating our best practices for building an AWS VPC.

This includes:
- Create the named VPC with appropriate tags
- Create a minimum of 3 subnets across multiple availability zones
- Create an internet gateway
- Create an IPv6 egress gateway
- Create a route table and associate the created subnets with it
- Create a routing table to include the relevant peers and their networks
- Create an RDS subnet group
"""
from pulumi import ComponentResource
from pulumi_aws import ec2

# TODO Vpc Component
class Vpc(pulumi.ComponentResource):
    """Pulumi component for building all of the necessary pieces of an AWS VPC.

    A component resource that encapsulates all of the standard practices of how the Dicey Tech
     Engineering team constructs and organizes VPC environments in AWS.
    """

    def __init__():
        """Build an AWS VPC with subnets, internet gateway, and routing table.
        :param vpc_config: Configuration object for customizing the created VPC and
            associated resources.
        :type vpc_config: OLVPCConfig
        :param opts: Optional resource options to be merged into the defaults.  Useful
            for handling things like AWS provider overrides.
        :type opts: Optional[ResourceOptions]
        """
        super.__init__("dt:netowrking:VPC")