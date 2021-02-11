"""
This module defines a Pulumi component resource for encapsulating our best practices for
building a MongoDB instance

This includes:
- Create the named EC2 with appropriate tags
- Create a Security Group
- Create a profile for the instance
- TODO Replica
"""

from typing import Optional, Text

from pulumi import ComponentResource, ResourceOptions, Output, info
from pulumi_aws import ec2, get_ami, GetAmiFilterArgs, iam
from pydantic import BaseModel, PositiveInt


# TODO Add deletion protection
# TODO Handle cluster
class DTMongoDBConfig(BaseModel):
    """
    Configuration object for defining configuration needed to create a
    MongoDB Instance.
    """

    name: Text
    vpc_id: Output[Text]
    subnet_id: Output[Text]
    instance_type: ec2.InstanceType
    volume_size: Optional[PositiveInt] = 8
    commands: Optional[Text]

    class Config:
        arbitrary_types_allowed = True


class DTMongoDB(ComponentResource):
    """
    Component to create a MongoDB instance with sane defaults and manage associated resources.

    """

    def __init__(self, instance_config: DTMongoDBConfig, opts: ResourceOptions = None):
        """
        Build an Educate instance.

        :param instance_config: Config object for customizing the created MongoDB instance
            and associated resources.
        :type DTMongoDBConfig

        :param opts: Optional resource options to be merged into the defaults.  Useful
            for handling things like AWS provider overrides.
        :type opts: Optional[ResourceOptions]
        """

        super().__init__(
            "diceytech:infrastructure:aws:database:DTMongoDB",
            f"{instance_config.name}-instance",
            opts,
        )

        self.tags = {"pulumi_managed": "true"}

        # Amazon Linux 2
        self.ami = get_ami(
            most_recent=True,
            owners=["137112412989"],  # x86_64
            filters=[
                GetAmiFilterArgs(name="name", values=["amzn2-ami-hvm-2.0.*"]),
                GetAmiFilterArgs(name="architecture", values=["x86_64"]),
            ],
        )

        security_group = ec2.SecurityGroup(
            f"{instance_config.name}-sg",
            vpc_id=instance_config.vpc_id,
            description="Enable HTTP and HTTPS access",
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
                    protocol=ec2.ProtocolType.TCP,
                    from_port=27017,
                    to_port=27017,
                    cidr_blocks=["0.0.0.0/0"],
                ),
            ],
            tags={**self.tags, "Name": f"{instance_config.name}"},
            opts=ResourceOptions(parent=self),
        )

        instance_assume_role_policy = iam.get_policy_document(
            statements=[
                iam.GetPolicyDocumentStatementArgs(
                    actions=["sts:AssumeRole"],
                    principals=[
                        iam.GetPolicyDocumentStatementPrincipalArgs(
                            type="Service",
                            identifiers=["ec2.amazonaws.com"],
                        )
                    ],
                )
            ],
        )

        mongodb_role = iam.Role(
            f"{instance_config.name}-role",
            assume_role_policy=instance_assume_role_policy.json,
            tags=self.tags,
            opts=ResourceOptions(parent=self),
        )

        ssm_role_policy_attach = iam.RolePolicyAttachment(  # noqa F841
            f"ssm-{instance_config.name}-policy-attach",
            role=mongodb_role.name,
            policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
            opts=ResourceOptions(parent=self),
        )

        s3_role_policy_attach = iam.RolePolicyAttachment(  # noqa F841
            f"s3-{instance_config.name}-policy-attach",
            role=mongodb_role.name,
            policy_arn="arn:aws:iam::aws:policy/AmazonS3FullAccess",
            opts=ResourceOptions(parent=self),
        )

        mongodb_profile = iam.InstanceProfile(
            f"{instance_config.name}-profile",
            role=mongodb_role.name,
            opts=ResourceOptions(parent=self),
        )

        self._instance = ec2.Instance(
            f"{instance_config.name}-instance",
            instance_type=instance_config.instance_type,
            subnet_id=instance_config.subnet_id,
            vpc_security_group_ids=[security_group.id],
            ami=self.ami.id,
            iam_instance_profile=mongodb_profile.id,
            root_block_device=ec2.InstanceRootBlockDeviceArgs(
                delete_on_termination=True,
                volume_size=instance_config.volume_size,
                encrypted=True,
            ),
            ebs_block_devices=[
                ec2.InstanceEbsBlockDeviceArgs(
                    device_name="/dev/sdf",
                    volume_size=20,
                    encrypted=True,
                    tags={**self.tags, "Name": "MongoDB Data"},
                ),
                ec2.InstanceEbsBlockDeviceArgs(
                    device_name="/dev/sdg",
                    volume_size=4,
                    encrypted=True,
                    tags={**self.tags, "Name": "MongoDB Journal"},
                ),
                ec2.InstanceEbsBlockDeviceArgs(
                    device_name="/dev/sdh",
                    volume_size=2,
                    encrypted=True,
                    tags={**self.tags, "Name": "MongoDB Log"},
                ),
            ],
            tags={**self.tags, "Name": "MongoDB Prod"},
            opts=ResourceOptions(parent=self),
        )

        self.register_outputs(
            {
                "private_dns": self._instance.private_dns,
                "instance_id": self._instance.id,
            }
        )

        info(msg=f"{instance_config.name} created.", resource=self)

    def get_private_dns(self) -> Text:
        return self._instance.private_dns

    def get_instance_id(self) -> Text:
        return self._instance.id
