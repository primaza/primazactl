import os
import argparse
import traceback
import sys
from pathlib import Path
from primazactl.types import \
    existing_file, kubernetes_name, semvertag_or_latest
from primazactl.primazamain.maincluster import MainCluster
from primazactl.primazaworker.workercluster import WorkerCluster
from primazactl.utils.kubeconfig import from_env
from primazactl.primazamain.constants import DEFAULT_TENANT
from primazactl.version import __primaza_version__


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
        default=__primaza_version__)

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
        default=from_env())

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
        required=True,
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
        default=from_env())

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
        default=DEFAULT_TENANT)


def join_cluster(args):

    try:
        main = MainCluster(
            context=args.tenant_context,
            namespace=args.tenant,
            kubeconfig_path=args.tenant_kubeconfig,
            config_file=None,
            version=None,
        )

        WorkerCluster(
            primaza_main=main,
            context=args.context,
            kubeconfig_file=args.kubeconfig,
            config_file=args.config,
            version=args.version,
            environment=args.environment,
            cluster_environment=args.cluster_environment,
            tenant=args.tenant,
        ).install_worker()

        print("Install and configure worker completed")
    except Exception as e:
        print(traceback.format_exc())
        print(f"\nAn exception occurred executing the "
              f"worker join function: {e}", file=sys.stderr)
        raise e
