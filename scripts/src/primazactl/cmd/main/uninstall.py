import argparse
import traceback
import sys
from .common import add_shared_args, validate
from primazactl.primazamain.maincluster import MainCluster


def add_uninstall(parser: argparse.ArgumentParser, parents=[]):
    uninstall_parser = parser.add_parser(
        "uninstall",
        help="Uninstall Primaza on target cluster",
        parents=parents)
    uninstall_parser.set_defaults(func=uninstall_primaza)
    add_shared_args(uninstall_parser)


def uninstall_primaza(args):
    validate(args)
    try:
        MainCluster(
            args.cluster_name,
            args.namespace,
            args.kubeconfig,
            args.config,
            args.version).uninstall_primaza()
        print("Primaza main successfully uninstalled")
    except Exception as e:
        print(traceback.format_exc())
        print(f"\nAn exception occurred executing main install: {e}",
              file=sys.stderr)
