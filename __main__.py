""" Open edX native deployment on AWS"""

import pulumi
from pulumi_aws import s3, ec2, ebs

config = pulumi.Config("instance")

tags = {
    "Name": "Open edX Pulumi",
    "pulumi_managed": "true",
    "AutoOff": "True",
    "Owner": "Sofiane",
}

group = ec2.SecurityGroup(
    "openedx-pulumi-sg",
    description="Enable SSH and HTTP ACcess",
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
            from_port=22,
            to_port=22,
            cidr_blocks=["0.0.0.0/0"],
        ),
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"],
        ),
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=18000,
            to_port=1899,
            cidr_blocks=["0.0.0.0/0"],
        ),
    ],
    tags=tags,
)

with open("config.sh") as f:
    user_data = f.read()

openedx = ec2.Instance(
    "openedx-native",
    ami=config.require("ubuntu_2004"),
    instance_type=config.require("instance_type"),
    vpc_security_group_ids=[group.id],
    user_data=user_data,
    tags=tags,
    key_name=config.get("keyName"),
    root_block_device=ec2.InstanceRootBlockDeviceArgs(
        delete_on_termination=True, volume_size=50
    ),
)

pulumi.export("publicIP", openedx.public_ip)
pulumi.export("publicHostname", openedx.public_dns)
