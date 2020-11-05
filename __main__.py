"""An AWS Python Pulumi program"""

import pulumi
import pulumi_aws as aws
from pulumi_aws import s3, ec2

config = pulumi.Config("instance")
key_name = config.get("keyName")

tags = {"Name": "openedx-pulumi", "AutoOff": "True", "Owner": "Sofiane"}

group = ec2.SecurityGroup(
    "openedx-pulumi-sg",
    description="Enable SSH and HTTP ACcess",
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
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
    ],
    tags=tags,
)


ami = aws.get_ami(
    most_recent=True,
    owners=["137112412989"],
    filters=[aws.GetAmiFilterArgs(name="name", values=["amzn-ami-hvm-*"])],
)


with open("config.sh") as f:
    user_data = f.read()

'''
user_data = """#!/bin/bash
echo "Hello, World!" > index.html
nohup python3 -m http.server 80 &
"""
'''

openedx = ec2.Instance(
    "openedx-native",
    ami=config.require("ubuntu_1604"),  # ami.id,
    instance_type=config.require("instance_type"),
    vpc_security_group_ids=[group.id],
    user_data=user_data,
    tags=tags,
    key_name=key_name,
)

pulumi.export("publicIP", openedx.public_ip)
pulumi.export("publicHostname", openedx.public_dns)
