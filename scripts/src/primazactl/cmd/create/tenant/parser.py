import argparse
import sys
import traceback
from primazactl.cmd.create.common import add_shared_args
from primazactl.primazamain.constants import DEFAULT_TENANT
from primazactl.types import kubernetes_name
from primazactl.utils import settings
from primazactl.utils import logger
from primazactl.cmd.apply.options import Options


def add_create_tenant(parser: argparse.ArgumentParser,
                      parents=[]):

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
            {DEFAULT_TENANT}")


def create_tenant(args):
    try:
        settings.set(args)

        # get tenant from options, even if the an options file was not
        # provided it sets the default values
        tenant = Options(args).get_tenant()

        # install the tenant, use command line args which will overwrite
        # values from options if specified.
        error = tenant.install(args.context,
                               args.tenant,
                               args.kubeconfig,
                               args.config,
                               args.version)
        if error:
            logger.log_error(f"Primaza tenant {tenant.tenant} "
                             f"install failed: {error}")
            return

        if settings.output_active():
            settings.output()
        elif settings.dry_run_active():
            print(f"Dry run create primaza tenant {tenant.tenant} "
                  "successfully completed.")
        else:
            # check tenant pod is running
            error_message = tenant.main.check()
            if error_message:
                print(f"Primaza tenant {tenant.tenant} create failed: "
                      f"{error_message}.")
            else:
                print(f"Create primaza tenant {tenant.tenant} "
                      f"successfully completed.")

    except Exception as e:
        if args.verbose:
            print(traceback.format_exc())
        logger.log_error("\nAn exception occurred executing tenant install:"
                         f"\n{e}", file=sys.stderr)
        raise e
