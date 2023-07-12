import argparse
import traceback
import sys
from primazactl.cmd.create.common import add_shared_args
from primazactl.primazamain.constants import DEFAULT_TENANT
from primazactl.primazamain.maincluster import MainCluster
from primazactl.types import kubernetes_name
from primazactl.utils import settings


def add_create_tenant(
        parser: argparse.ArgumentParser,
        parents=[],
):
    tenant_parser = parser.add_parser(
            "tenant",
            help="Create a Primaza tenant",
            parents=parents)
    tenant_parser.set_defaults(func=create_tenant)
    add_shared_args(tenant_parser)
    add_args_tenant(tenant_parser)


def add_args_tenant(parser: argparse.ArgumentParser):
    parser.add_argument(
        "tenant",
        type=kubernetes_name,
        nargs='?',
        help=f"tenant to create. Default: \
            {DEFAULT_TENANT}",
        default=DEFAULT_TENANT)


def create_tenant(args):
    try:
        settings.set(args)
        MainCluster(
            args.context,
            args.tenant,
            args.kubeconfig,
            args.config,
            args.version).install_primaza()

        if settings.output_active():
            settings.output()
        elif settings.dry_run_active():
            print("Dry run Primaza tenant install complete")
        else:
            print("Primaza tenant installed")

    except Exception as e:
        if args.verbose:
            print(traceback.format_exc())
            print(f"\nAn exception occurred executing tenant install: {e}",
                  file=sys.stderr)
        raise e
