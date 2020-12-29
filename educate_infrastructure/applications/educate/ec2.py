"""This module defines a Pulumi component resource for encapsulating our best practices for building an AWS EC2.

This includes:
- TODO Create the named EC2 with appropriate tags
- TODO Create a minimum of 3 subnets across multiple availability zones
- TODO Create an internet gateway
- TODO Create an IPv6 egress gateway (Why??)
- TODO  Create a route table and associate the created subnets with it
- TODO Create a routing table to include the relevant peers and their networks
"""

from pulumi import ComponentResource
from pulumi_aws import ec2, get_ami, GetAmiFilterArgs


# TODO Make the SecurityGroup an input parameter
# TODO Add SSM role to instances in private subnets
class DTEc2(ComponentResource):
    """Pulumi component for building all of the necessary pieces of an AWS EC2 instnace.

    A component resource that encapsulates all of the standard practices of how the Dicey Tech
     Engineering team constructs and deploys EC2 environments in AWS.
    """

    def __init__(
        self, name: str, app_vpc_id: str, app_subnet_id: str, iam_instance_profile: str
    ):
        """
        Build an AWS EC2 instance with subnets, internet gateway, and routing table.

        :param name: Configuration object for customizing the created VPC and
            associated resources.
        :type String
        :param name: Configuration object for customizing the created VPC and
            associated resources.
        :type String
        :param name: Configuration object for customizing the created VPC and
            associated resources.
        :type String
        """
        self.name = name
        self.tags = {"pulumi_managed": "true"}
        super().__init__("diceytech:infrastructure:aws:EC2", f"{self.name}-instance")

        self.size = "t2.micro"

        # Ubuntu 20.04 LTS - Focal
        self.ami = get_ami(
            most_recent=True,
            owners=["137112412989"],
            filters=[GetAmiFilterArgs(name="name", values=["amzn-ami-hvm-*"])],
        )

        # TODO Abstract SecurityGroup
        self.group = ec2.SecurityGroup(
            f"{self.name}-sg",
            vpc_id=app_vpc_id,
            description="Enable HTTP access",
            egress=[
                ec2.SecurityGroupEgressArgs(
                    protocol="-1",
                    from_port=0,
                    to_port=0,
                    cidr_blocks=["0.0.0.0/0"],
                )
            ],
            ingress=[
                ec2.SecurityGroupIngressArgs(
                    protocol="tcp",
                    from_port=80,
                    to_port=80,
                    cidr_blocks=["0.0.0.0/0"],
                ),
                ec2.SecurityGroupIngressArgs(
                    protocol="tcp",
                    from_port=18000,
                    to_port=18999,
                    cidr_blocks=["0.0.0.0/0"],
                ),
            ],
        )
        # TODO Smells bad....
        with open("config.sh") as f:
            self.user_data = f.read()

        self._instance = ec2.Instance(
            f"{self.name}-instance",
            instance_type=self.size,
            subnet_id=app_subnet_id,
            vpc_security_group_ids=[self.group.id],
            user_data=self.user_data,
            ami="ami-0a76049070d0f8861",
            iam_instance_profile=iam_instance_profile,
            root_block_device=ec2.InstanceRootBlockDeviceArgs(
                delete_on_termination=True, volume_size=50
            ),
        )

    def get_public_ip(self):
        return self.server.public_ip

    def get_public_dns(self):
        return self.server.public_dns