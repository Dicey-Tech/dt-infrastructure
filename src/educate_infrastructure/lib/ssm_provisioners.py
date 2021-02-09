import abc
import json
import boto3
import pulumi
from typing import Any, Optional
from typing_extensions import TypedDict
from uuid import uuid4

from pulumi import dynamic


class ConnectionArgs(TypedDict):
    instance_id: pulumi.Input[str]
    session_document: pulumi.Input[str]
    script_document: pulumi.Input[str]  # "AWS-RunShellScript"


class ProvisionerProvider(dynamic.ResourceProvider):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def on_create(self, inputs: Any) -> Any:
        return

    def create(self, inputs):
        outputs = self.on_create(inputs)
        return dynamic.CreateResult(id_=uuid4().hex, outs=outputs)

    def diff(self, _id, olds, news):
        # If anything changed in the inputs, replace the resource.
        diffs = []
        for key in olds:
            if key not in news:
                diffs.append(key)
            else:
                olds_value = json.dumps(olds[key], sort_keys=True, indent=2)
                news_value = json.dumps(news[key], sort_keys=True, indent=2)
                if olds_value != news_value:
                    diffs.append(key)
        for key in news:
            if key not in olds:
                diffs.append(key)

        return dynamic.DiffResult(
            changes=len(diffs) > 0, replaces=diffs, delete_before_replace=True
        )


class RunCommandResult(TypedDict):
    stdout: str
    """The stdout of the command that was executed."""
    stderr: str
    """The stderr of the command that was executed."""


# TODO catch error when command fails
class RemoteExecProvider(ProvisionerProvider):
    def on_create(self, inputs: Any) -> Any:
        ssm = boto3.client("ssm")
        session = ssm.start_session(
            Target=inputs["conn"]["instance_id"],
            DocumentName="SSM-SessionManagerRunShell",
        )

        try:
            results = []
            output = ssm.send_command(
                InstanceIds=[inputs["conn"]["instance_id"]],
                DocumentName=inputs["conn"]["script_document"],
                Parameters={"commands": inputs["commands"]},
            )

            command_id = output.get("Command", {}).get("CommandId", None)

            command_invocation = ssm.list_command_invocations(  # noqa F841
                CommandId=command_id, Details=True
            )["CommandInvocations"]

            results.append(
                {
                    "CommandId": output["Command"]["CommandId"],
                    "Status": command_invocation,
                }
            )
        finally:
            ssm.terminate_session(SessionId=session["SessionId"])
            pulumi.info(f"results: {results}")
        return inputs


class RemoteExec(dynamic.Resource):
    # results: pulumi.Output[list]

    def __init__(
        self,
        name: str,
        conn: ConnectionArgs,
        commands: list,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        self.conn = conn
        """conn contains information on how to connect to the destination, in addition to dependency information."""
        self.commands = commands
        """The commands to execute. Exactly one of 'command' and 'commands' is required."""
        self.results = []
        """The resulting command outputs."""

        super().__init__(
            RemoteExecProvider(),
            name,
            {
                "conn": conn,
                "commands": commands,
                "results": None,
            },
            opts,
        )
