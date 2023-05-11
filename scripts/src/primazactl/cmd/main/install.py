import argparse
import traceback
import sys
from .common import add_shared_args, validate
from primazactl.primazamain.maincluster import MainCluster


def add_install(parser: argparse.ArgumentParser, parents=[]):
    install_parser = parser.add_parser(
        name="install",
        help="Install Primaza on target cluster",
        parents=parents)
    install_parser.set_defaults(func=install_primaza)
    add_shared_args(install_parser)


def install_primaza(args):
    validate(args)
    try:
        MainCluster(
            args.cluster_name,
            args.namespace,
            args.kubeconfig,
            args.config,
            args.version).install_primaza()
        print("Primaza main installed")
    except Exception as e:
        print(traceback.format_exc())
        print(f"\nAn exception occurred executing main install: {e}",
              file=sys.stderr)
