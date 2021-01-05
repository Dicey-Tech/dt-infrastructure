""" RDS """
from enum import Enum
from typing import Dict, List, Optional, Text, Union

from pulumi import ComponentResource, Output
from pulumi_aws import rds
from pulumi_aws.ec2 import SecurityGroup
from pydantic import BaseModel, PositiveInt, SecretStr, conint

from educate_infrastructure.lib.dt_types import AWSBase

MAX_BACKUP_DAYS = 35


class StorageType(str, Enum):  # noqa: WPS600
    """Container for constraining available selection of storage types."""

    magnetic = "standard"
    ssd = "gp2"
    performance = "io1"


class DTReplicaDBConfig(BaseModel):
    """Configuration object for defining configuration needed to create a read replica."""

    instance_size: Text = "db.t3.small"
    storage_type: StorageType = StorageType.ssd
    public_access: bool = False
    security_groups: Optional[List[SecurityGroup]] = None


class DTRDSConfig(AWSBase):
    """Configuration object for defining the interface to create an RDS instance with sane defaults."""

    engine: Text
    engine_version: Text
    instance_name: Text  # The name of the RDS instance
    password: SecretStr
    parameter_overrides: List[Dict[Text, Union[Text, bool, int, float]]]  # noqa: WPS234
    port: PositiveInt
    # subnet_group_name: Union[Text, Output[str]]
    security_groups: List[SecurityGroup]
    backup_days: conint(ge=0, le=MAX_BACKUP_DAYS, strict=True) = 30  # type: ignore
    db_name: Optional[Text] = None  # The name of the database schema to create
    instance_size: Text = "db.t2.large"
    is_public: bool = False
    max_storage: Optional[PositiveInt] = None  # Set to allow for storage autoscaling
    multi_az: bool = False
    prevent_delete: bool = False  # TODO Change to true
    public_access: bool = False
    take_final_snapshot: bool = True
    storage: PositiveInt = PositiveInt(50)  # noqa: WPS432
    storage_type: StorageType = StorageType.ssd
    username: Text = "dtdevops"
    read_replica: Optional[DTReplicaDBConfig] = None


class DTMySQLConfig(DTRDSConfig):
    """Configuration container to specify settings specific to MySQL."""

    engine: Text = "mysql"
    engine_version: Text = "5.7"
    port: PositiveInt = PositiveInt(3306)
    instance_size: Text = "db.t2.large"

    family: Text = "mysql5.7"


class DTRDSInstance(ComponentResource):
    """
    Build an RDS Instance

    """

    def __init__(self, db_config: DTRDSConfig):
        """Create an RDS instance, parameter group, and optionally read replica.

        :param db_config: Configuration object for customizing the deployed database instance.
        :type db_config: DTRDSConfig

        :returns: The constructed component resource object.

        :rtype: DTRDSInstance
        """
        super().__init__(
            "ol:infrastructure:aws:database:DTRDSInstance",
            db_config.instance_name,
            None,
        )

        self.parameter_group = rds.ParameterGroup(
            f"{db_config.instance_name}-{db_config.engine}-parameter-group",
            # family=parameter_group_family(db_config.engine, db_config.engine_version),
            family=db_config.family,
            name=f"{db_config.instance_name}-{db_config.engine}-parameter-group",
        )

        self.db_instance = rds.Instance(
            f"{db_config.instance_name}-{db_config.engine}-instance",
            allocated_storage=db_config.storage,
            auto_minor_version_upgrade=True,
            backup_retention_period=db_config.backup_days,
            copy_tags_to_snapshot=True,
            # db_subnet_group_name=db_config.subnet_group_name,
            deletion_protection=db_config.prevent_delete,
            engine=db_config.engine,
            engine_version=db_config.engine_version,
            final_snapshot_identifier=f"{db_config.instance_name}-{db_config.engine}-final-snapshot",
            identifier=db_config.instance_name,
            instance_class=db_config.instance_size,
            max_allocated_storage=db_config.max_storage,
            multi_az=db_config.multi_az,
            name=db_config.db_name,
            opts=resource_options,
            parameter_group_name=self.parameter_group.name,
            password=db_config.password.get_secret_value(),
            port=db_config.port,
            publicly_accessible=db_config.is_public,
            skip_final_snapshot=not db_config.take_final_snapshot,
            storage_encrypted=True,
            storage_type=db_config.storage_type.value,
            tags=db_config.tags,
            username=db_config.username,
            vpc_security_group_ids=[group.id for group in db_config.security_groups],
        )

        component_outputs = {
            "parameter_group": self.parameter_group,
            "rds_instance": self.db_instance,
        }

        self.register_outputs(component_outputs)