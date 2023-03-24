import argparse
from .common import add_shared_args, validate
from primazactl.primazamain.primazamain import PrimazaMain


def add_uninstall(parser: argparse.ArgumentParser, parents=[]):
    uninstall_parser = parser.add_parser(
        "uninstall",
        help="Uninstall Primaza on target cluster",
        parents=parents)
    uninstall_parser.set_defaults(func=uninstall_primaza)
    add_shared_args(uninstall_parser)


def uninstall_primaza(args):
    validate(args)

    PrimazaMain(
        args.cluster_name,
        args.kubeconfig,
        args.config,
        args.version).uninstall_primaza()
