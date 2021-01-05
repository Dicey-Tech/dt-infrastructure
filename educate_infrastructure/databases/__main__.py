"""Manage the creation of an RDS instance 
and a MongoDB instance deployed in an EC2 instance.


"""
from pulumi import Config, get_stack, export, StackReference
from pulumi_aws import ec2, get_ami

from rds import DTMySQLConfig, DTRDSInstance

env = get_stack()
network_stack = StackReference(f"BbrSofiane/networking/prod")
db_vpc_id = network_stack.get_output("db_vpc_id")
db_private_subnet_ids = network_stack.get_output("db_private_subnet_ids")

# TODO Provison RDS Instance
mysql_db_sg = ec2.SecurityGroup(
    f"mysql-db-sg-{env}",
    description="Access from the database VPC to the MySQL database",
    ingress=[
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=3306,
            to_port=3306,
            # TODO add educate app security_groups=[redash_instance_security_group.id],
            description="MySQL access from Educate App instances",
        ),
    ],
    egress=[
        ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
        )
    ],
    # tags=aws_config.merged_tags({"Name": f"redash-db-access-{redash_environment}"}),
    vpc_id=db_vpc_id,
)

mysql_db_config = DTMySQLConfig(
    instance_name=f"mysql-db-{env}",
    # username= ""
    password="password",
    security_groups=[mysql_db_sg],
    db_name="mysql",
)

mysql_db = DTRDSInstance(db_config=DTRDSConfig)

# TODO Provision MongoDB Instance

export(
    "mysql_endpoint",
    mysql_db.endpoint,
)