import argparse
import traceback
import sys
from .common import add_shared_args
from primazactl.primazamain.maincluster import MainCluster


def add_delete_tenant(parser: argparse.ArgumentParser, parents=[]):
    delete_parser = parser.add_parser(
        "tenant",
        help="delete Primaza tenant on target cluster",
        parents=parents)
    delete_parser.set_defaults(func=delete_tenant)
    add_shared_args(delete_parser)


def delete_tenant(args):
    try:
        MainCluster(
            args.context,
            args.namespace,
            args.kubeconfig,
            args.config,
            args.version).delete_primaza()
        print("Primaza main successfully deleted")
    except Exception as e:
        print(traceback.format_exc())
        print(f"\nAn exception occurred executing main install: {e}",
              file=sys.stderr)
        raise e
