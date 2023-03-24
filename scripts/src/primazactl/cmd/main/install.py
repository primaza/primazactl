import argparse
from .common import add_shared_args, validate
from primazactl.primazamain.primazamain import PrimazaMain


def add_install(parser: argparse.ArgumentParser, parents=[]):
    install_parser = parser.add_parser(
        name="install",
        help="Install Primaza on target cluster",
        parents=parents)
    install_parser.set_defaults(func=install_primaza)
    add_shared_args(install_parser)


def install_primaza(args):
    validate(args)

    PrimazaMain(
        args.cluster_name,
        args.kubeconfig,
        args.config,
        args.version).install_primaza()
