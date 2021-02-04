"""This module defines a Pulumi component resource for encapsulating our best practices for building an AWS EC2.

This includes:
- Create the named EC2 with appropriate tags
"""
# TODO Abstract Security Group so that there is no need to create a SG per instance
from typing import List, Text, Optional

from pulumi import ComponentResource, Output
from pulumi_aws import ec2, get_ami, GetAmiFilterArgs, iam
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


# TODO Make the SecurityGroup an input parameter
class DTEc2(ComponentResource):
    """Pulumi component for building all of the necessary pieces of an AWS EC2 instnace.

    A component resource that encapsulates all of the standard practices of how the Dicey Tech
    Engineering team constructs and deploys EC2 environments in AWS.
    """

    def __init__(self, instance_config: DTEducateConfig):
        """
        Build an Educate instance.

        :param instance_config: Config object for customizing the created Educate instance
            and associated resources.
        :type DTEducateConfig
        """
        self.name = instance_config.name
        self.tags = {"pulumi_managed": "true", "Name": self.name}
        super().__init__("diceytech:infrastructure:aws:EC2", f"{self.name}-instance")

        self.size = instance_config.instance_type

        # Ubuntu 20.04 LTS - Focal
        self.ami = get_ami(
            most_recent=True,
            owners=["137112412989"],
            filters=[GetAmiFilterArgs(name="name", values=["amzn-ami-hvm-*"])],
        )

        # TODO Smells bad....
        with open("config.sh") as f:
            self.user_data = f.read()

        self._instance = ec2.Instance(
            f"{self.name}-instance",
            instance_type=self.size,
            subnet_id=instance_config.app_subnet_id,
            vpc_security_group_ids=[instance_config.security_group_id],
            user_data=self.user_data,
            ami="ami-0a76049070d0f8861",
            iam_instance_profile=instance_config.iam_instance_profile_id,
            root_block_device=ec2.InstanceRootBlockDeviceArgs(
                delete_on_termination=True, volume_size=instance_config.volume_size
            ),
            tags=self.tags,
        )

    def get_public_ip(self) -> Text:
        return self._instance.public_ip

    def get_public_dns(self) -> Text:
        return self._instance.public_dns

    def get_instance_id(self) -> Text:
        return self._instance.id

    @staticmethod
    def get_required_records(env: str) -> List[str]:
        if env == "dev":
            return ["discovery", "preview", "studio"]
        else:
            return [
                "blockstore",
                "credentials",
                "discovery",
                "forum",
                "insights",
                "notes",
                "preview",
                "shop",
                "studio",
            ]
