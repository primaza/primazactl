import argparse
import traceback
import sys
from .common import add_shared_args
from primazactl.primazamain.constants import DEFAULT_TENANT
from primazactl.types import kubernetes_name
from primazactl.cmd.apply.options import Options


def add_delete_tenant(parser: argparse.ArgumentParser, parents=[]):
    delete_parser = parser.add_parser(
        "tenant",
        help="delete Primaza tenant on target cluster",
        parents=parents)
    delete_parser.set_defaults(func=delete_tenant)
    add_args_tenant(delete_parser)
    add_shared_args(delete_parser)


def add_args_tenant(parser: argparse.ArgumentParser):
    parser.add_argument(
        "tenant",
        type=kubernetes_name,
        nargs='?',
        help=f"tenant to delete. Default: \
            {DEFAULT_TENANT}")


def delete_tenant(args):
    try:
        tenant = Options(args).get_tenant()
        tenant.delete(args.context,
                      args.tenant,
                      args.kubeconfig,
                      args.config,
                      args.version)
        print(f"Primaza tenant {tenant.tenant} successfully deleted.")
    except Exception as e:
        print(traceback.format_exc())
        print(f"\nAn exception occurred executing main install: {e}",
              file=sys.stderr)
        raise e
