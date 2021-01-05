from ipaddress import IPv4Network

import pulumi
import pytest

from educate_infrastructure.infra.network.tests import networking_mock
from educate_infrastructure.infra.network.vpc import DTVpc


class FakeIPv4Network(object):
    def __init__(self):
        pass


# TODO test to verify that there az_count match the number of subnets
class TestAppsVpc(object):
    """ Initial tests doing basic coverage """

    def setup(self):
        self.name = "educate-app-vpc"
        self.az_count = 2

        self.cidr_block = IPv4Network("172.255.100.0/16", False)

        self.test_vpc = DTVpc(
            name=self.name, az_count=self.az_count, cidr_block=self.cidr_block
        )

    @pulumi.runtime.test
    def test_vpc_created(self):
        def check_name(args):
            resource_name = args[0]
            assert resource_name == self.name

        return pulumi.Output.all(self.test_vpc.name).apply(check_name)

    # TODO Create Base Class https://github.com/mitodl/ol-infrastructure/blob/87021e2a8681c769354c1b227328433adaa1af15/src/ol_infrastructure/lib/ol_types.py#L45
    @pulumi.runtime.test
    def test_vpc_has_required_tags(self):
        def check_tags(args):
            tags = args[0]
            assert tags is not None
            assert "pulumi_managed" in tags

        return pulumi.Output.all(self.test_vpc.tags).apply(check_tags)

    @pulumi.runtime.test
    def test_vpc_has_public_subnet(self):
        def check_public_subnet(args):
            public_subnet_ids = args[0]
            assert len(public_subnet_ids) == self.az_count

        return pulumi.Output.all(self.test_vpc.get_public_subnet_ids()).apply(
            check_public_subnet
        )

    @pulumi.runtime.test
    def test_vpc_has_private_subnet(self):
        def check_private_subnet(args):
            private_subnet_ids = args[0]
            assert len(private_subnet_ids) == self.az_count

        return pulumi.Output.all(self.test_vpc.get_private_subnet_ids()).apply(
            check_private_subnet
        )
