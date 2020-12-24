import pytest
import pulumi

# TODO move mock to its own file
class PulumiMock(pulumi.runtime.Mocks):
    def new_resource(self, token, name, inputs, provider, id_):
        outputs = inputs
        if token == "aws:ec2/instance:Instance":
            outputs = {
                **inputs,
                "publicIp": "203.0.113.12",
                "publicDns": "ec2-203-0-113-12.compute-1.amazonaws.com",
            }
        return [name + "_id", outputs]

    # https://github.com/pulumi/pulumi/blob/8a9b381767c5d14ad2181c41ede4266cd196c839/sdk/python/lib/pulumi/runtime/mocks.py#L40
    def call(self, token, args, provider):
        # https://github.com/pulumi/pulumi-aws/blob/ddc4d5623c8bb2e25428f11ab0de487b17795614/sdk/python/pulumi_aws/get_availability_zones.py#L206
        if token == "aws:index/getAvailabilityZones:getAvailabilityZones":
            return {"names": ["eu-west-2a", "eu-west-2b", "eu-west-2c"]}
        # https://github.com/pulumi/pulumi-aws/blob/ddc4d5623c8bb2e25428f11ab0de487b17795614/sdk/python/pulumi_aws/get_ami.py#L487
        if token == "aws:index/getAmi:getAmi":
            return {"architecture": "x86_64", "id": "ami-0eb1f3cdeeb8eed2a"}
        return {}


pulumi.runtime.set_mocks(PulumiMock())

from educate_infrastructure.networking.__main__ import apps_vpc


class TestAppsVpc(object):
    """ Initial tests doing basic coverage """

    def setup(self):
        pass

    @pulumi.runtime.test
    def test_vpc_tags(self):
        def check_tags(args):
            urn, tags = args
            assert tags is not None
            assert "pulumi_managed" in tags

        return pulumi.Output.all(apps_vpc.urn, apps_vpc.tags).apply(check_tags)