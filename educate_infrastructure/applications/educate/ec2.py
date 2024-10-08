"""
This module defines a Pulumi component resource for encapsulating our best practices for
building an Educate Instance.

This includes:
- Create the named EC2 with appropriate tags
"""
from typing import List, Text, Optional

from pulumi import ComponentResource, Output, ResourceOptions, info
from pulumi_aws import ec2, GetAmiFilterArgs, iam
from pydantic import BaseModel, PositiveInt


class DTEducateConfig(BaseModel):
    """
    Configuration object for defining configuration needed to create a native
    Open edX Instance.
    """

    name: Text
    app_vpc_id: Output
    app_subnet_id: Output
    iam_instance_profile_id: Output
    security_group_id: Output
    instance_type: ec2.InstanceType
    volume_size: Optional[PositiveInt] = 50
    commands: Optional[Text]

    class Config:
        arbitrary_types_allowed = True


class DTEc2(ComponentResource):
    """Pulumi component for building all of the necessary pieces of an AWS EC2 instnace.

    A component resource that encapsulates all of the standard practices of how the Dicey Tech
    Engineering team constructs and deploys EC2 environments in AWS.
    """

    def __init__(self, instance_config: DTEducateConfig, opts: ResourceOptions = None):
        """
        Build an Educate instance.

        :param instance_config: Config object for customizing the created Educate instance
            and associated resources.
        :type DTEducateConfig

        :param opts: Optional resource options to be merged into the defaults.  Useful
            for handling things like AWS provider overrides.
        :type opts: Optional[ResourceOptions]
        """
        self.name = instance_config.name
        self.tags = {"pulumi_managed": "true", "Name": self.name}
        super().__init__(
            "diceytech:infrastructure:aws:EC2", f"{self.name}-instance", opts
        )

        self.size = instance_config.instance_type

        # Ubuntu 20.04 LTS - Focal
        self.ami = ec2.get_ami(
            most_recent=True,
            owners=["679593333241"],
            filters=[
                GetAmiFilterArgs(
                    name="name",
                    values=["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"],
                ),
            ],
        )

        # TODO Smells bad....
        with open("config.sh") as f:
            self.user_data = f.read()

        self._instance = ec2.Instance(
            f"{self.name}-instance",
            instance_type=self.size,
            subnet_id=instance_config.app_subnet_id,
            vpc_security_group_ids=[instance_config.security_group_id],
            # user_data=self.user_data,
            ami="ami-08616bba875264c0b",  # self.ami.id,
            iam_instance_profile=instance_config.iam_instance_profile_id,
            root_block_device=ec2.InstanceRootBlockDeviceArgs(
                delete_on_termination=True,
                volume_size=instance_config.volume_size,
                encrypted=True,
            ),
            tags=self.tags,
            disable_api_termination=True,
            opts=ResourceOptions(parent=self),
        )

        self.register_outputs(
            {
                "public_ip": self._instance.public_ip,
                "public_dns": self._instance.public_dns,
                "instance_id": self._instance.id,
            }
        )

        info(msg=f"{self.name} created.", resource=self)

    def get_public_ip(self) -> Text:
        return self._instance.public_ip

    def get_public_dns(self) -> Text:
        return self._instance.public_dns

    def get_instance_id(self) -> Text:
        return self._instance.id
