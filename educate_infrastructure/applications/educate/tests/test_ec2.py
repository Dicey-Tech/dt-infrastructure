import pytest
import pulumi

from educate_infrastructure.applications.educate.tests import educate_mock
from educate_infrastructure.applications.educate.ec2 import DTEc2


class TestEducateApp(object):
    """ Initial tests doing some basic coverage"""

    def setup(self):
        self.name = "educate-app-instance"
        self.public_instance = DTEc2(
            name=f"{self.name}-public",
            app_vpc_id="vpc-0d905953c8537847c",
            app_subnet_id="subnet-0d06af077da3e1c6f",
            iam_instance_profile="educate-app-role-de9eb13",
        )

    @pulumi.runtime.test
    def test_ec2_has_required_tags(self):
        def check_tags(args):
            tags = args[0]
            assert tags is not None
            assert "pulumi_managed" in tags

        return pulumi.Output.all(self.public_instance.tags).apply(check_tags)

    @pulumi.runtime.test
    def test_ec2_has_id(self):
        def check_id(args):
            instance_id = args[0]
            assert instance_id is not None

        return pulumi.Output.all(self.public_instance.get_instance_id()).apply(check_id)