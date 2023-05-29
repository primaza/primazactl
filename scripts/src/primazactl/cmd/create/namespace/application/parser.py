import argparse
from primazactl.cmd.create.namespace.common import create_application_namespace
from primazactl.cmd.create.namespace.common import add_args_namespace
from primazactl.cmd.create.namespace.constants import APPLICATION


def add_create_application_namespace(
        parser: argparse.ArgumentParser,
        parents=[],
):
    application_namespace_parser = parser.add_parser(
            "application-namespace",
            help="Create an application namespace",
            parents=parents)
    application_namespace_parser.set_defaults(
            func=create_application_namespace)
    add_args_namespace(application_namespace_parser, APPLICATION)
