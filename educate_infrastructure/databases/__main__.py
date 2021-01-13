"""Manage the creation of an RDS instance
and a MongoDB instance deployed in an EC2 instance.


"""
from pulumi import Config, get_stack, export, StackReference
from pulumi_aws import ec2, get_ami

from rds import DTMySQLConfig, DTRDSInstance

env = get_stack()
network_stack = StackReference("BbrSofiane/networking/prod")
db_vpc_id = network_stack.get_output("db_vpc_id")
db_private_subnet_ids = network_stack.get_output("db_private_subnet_ids")
db_subnet_group_name = network_stack.get_output("db_subnet_group_name")

# TODO Provison RDS Instance
mysql_db_sg = ec2.SecurityGroup(
    f"mysql-db-sg-{env}",
    description="Access from the database VPC to the MySQL database",
    ingress=[
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=3306,
            to_port=3306,
            cidr_blocks=["0.0.0.0/0"],
            description="MySQL access from Educate App instances",
        ),
    ],
    vpc_id=db_vpc_id,
)

mysql_db_config = DTMySQLConfig(
    instance_name=f"educate-sql-db-{env}",
    subnet_group_name=db_subnet_group_name,
    password="password",
    security_groups=[mysql_db_sg],
    db_name="educate_db",
    tags={"pulumi_managed": "True"},
    # snapshot_identifier="educate-sql-db-2-final-snapshot",
)

mysql_db = DTRDSInstance(db_config=mysql_db_config)

# TODO Provision MongoDB Instance

export("mysql_endpoint", mysql_db.get_endpoint())
