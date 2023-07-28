import os
import argparse
import traceback
import sys
from pathlib import Path
from primazactl.types import \
    existing_file, kubernetes_name, semvertag_or_latest
from primazactl.primazamain.constants import DEFAULT_TENANT
from primazactl.version import __primaza_version__
from primazactl.utils import settings
from primazactl.cmd.options.options import Options
from primazactl.utils import logger


def add_group(parser: argparse.ArgumentParser, parents=[]):
    join_parser = parser.add_parser(
        name="join",
        help="Join Cluster",
        parents=parents)

    join_subparsers = join_parser.add_subparsers()
    join_cluster_parser = join_subparsers.add_parser(
        name="cluster",
        help="Join Cluster",
        parents=parents)

    join_cluster_parser.set_defaults(func=join_cluster)
    add_args_join(join_cluster_parser)
    return join_cluster_parser


def add_args_join(parser: argparse.ArgumentParser):
    # primazactl
    parser.add_argument(
        "-f", "--config",
        dest="config",
        type=existing_file,
        required=False,
        help="primaza config file. Takes precedence over --version")

    parser.add_argument(
        "-v", "--version",
        dest="version",
        required=False,
        help=f"Version of primaza to use, default: {__primaza_version__}. "
             "Ignored if --config is set.",
        type=semvertag_or_latest,
        default=None)

    parser.add_argument("-p", "--options",
                        dest="options_file",
                        type=existing_file,
                        required=False,
                        help="primaza options file in which default "
                             "command line options are specified. Options "
                             "set on the command line take precedence.")

    # worker
    parser.add_argument(
        "-c", "--context",
        dest="context",
        type=str,
        required=False,
        help="name of cluster, as it appears in kubeconfig, \
                  to join, default: \
                  current kubeconfig context",
        default=None)

    parser.add_argument(
        "-k", "--kubeconfig",
        dest="kubeconfig",
        required=False,
        help=f"path to kubeconfig file, default: KUBECONFIG \
                   environment variable if set, otherwise \
                   {(os.path.join(Path.home(),'.kube','config'))}",
        type=existing_file,
        default=None)

    parser.add_argument(
        "-u", "--internal-url",
        dest="internal_url",
        required=False,
        help="the url used by Primaza's Control Plane to \
                   reach the joined cluster",
        type=str,
        default=None)

    # main
    parser.add_argument(
        "-d", "--cluster-environment",
        dest="cluster_environment",
        type=kubernetes_name,
        required=True,
        help="name to use for the ClusterEnvironment that \
                will be created in Primaza")

    parser.add_argument(
        "-e", "--environment",
        dest="environment",
        type=kubernetes_name,
        required=False,
        help="the Environment that will be associated to \
                the ClusterEnvironment")

    parser.add_argument(
        "-l", "--tenant-kubeconfig",
        dest="tenant_kubeconfig",
        required=False,
        help=f"path to kubeconfig file for the tenant, default: KUBECONFIG \
                   environment variable if set, otherwise \
                   {(os.path.join(Path.home(),'.kube','config'))}",
        type=existing_file,
        default=None)

    parser.add_argument(
        "-m", "--tenant-context",
        dest="tenant_context",
        required=False,
        help="name of cluster, as it appears in kubeconfig, \
                on which primaza tenant was created. Default: \
                current kubeconfig context",
        type=str,
        default=None)

    parser.add_argument(
        "-t", "--tenant",
        dest="tenant",
        type=kubernetes_name,
        required=False,
        help=f"tenant to use for join. Default: \
            {DEFAULT_TENANT}",
        default=None)

    # options
    parser.add_argument(
        "-y", "--dry-run",
        dest="dry_run",
        type=str,
        required=False,
        choices=settings.DRY_RUN_CHOICES,
        default=settings.DRY_RUN_NONE,
        help=f"Set for dry run (default: {settings.DRY_RUN_NONE})")

    parser.add_argument(
        "-o", "--output",
        dest="output_type",
        type=str,
        required=False,
        choices=settings.OUTPUT_CHOICES,
        default=settings.OUTPUT_NONE,
        help="Set to get output of resources which are created "
             f"(default: {settings.OUTPUT_NONE}).")


def join_cluster(args):

    try:

        if not args.options_file:
            if not args.environment and args.cluster_environment:
                print("[ERROR] must specify either an options file or both "
                      "a cluster environment and an environment")
                return

        settings.set(args)

        options = Options(args)
        tenant = options.get_tenant()
        error = tenant.create_only(args.tenant_context,
                                   args.tenant,
                                   args.tenant_kubeconfig,
                                   None)

        cluster_environment = options.get_cluster_environment(
            args.cluster_environment, tenant)

        if error:
            logger.log_error(f"Join cluster {cluster_environment.name} "
                             f"failed: {error}")
            return

        error = cluster_environment.join(args.cluster_environment,
                                         args.context,
                                         args.kubeconfig,
                                         args.environment,
                                         args.config,
                                         args.version,
                                         args.internal_url)

        if error:
            logger.log_error(f"Join cluster {cluster_environment.name} "
                             f"failed: {error}")
        elif settings.output_active():
            settings.output()
        elif settings.dry_run_active():
            print(f"Dry run join cluster {cluster_environment.name} "
                  f"successfully completed")
        else:
            print(f"Join cluster {cluster_environment.name} "
                  "successfully completed")
    except Exception as e:
        print(traceback.format_exc())
        logger.log_error(f"\nAn exception occurred executing the "
                         f"worker join function: {e}", file=sys.stderr)
        raise e
