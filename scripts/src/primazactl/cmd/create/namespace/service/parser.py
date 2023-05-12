import argparse
from primazactl.cmd.create.namespace.common import create_service_namespace
from primazactl.cmd.create.namespace.common import add_args_namespace
from primazactl.cmd.create.namespace.constants import SERVICE


def add_create_service_namespace(
        parser: argparse.ArgumentParser,
        parents=[],
):
    service_namespace_parser = parser.add_parser(
            "service-namespace",
            help="Create a service namespace",
            parents=parents)
    service_namespace_parser.set_defaults(func=create_service_namespace)
    add_args_namespace(service_namespace_parser, SERVICE)
