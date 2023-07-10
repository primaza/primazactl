import argparse
import traceback
import sys
import os
from pathlib import Path
from primazactl.types import kubernetes_name, \
    existing_file, \
    semvertag_or_latest
from primazactl.primazaworker.workernamespace import WorkerNamespace
from primazactl.primazaworker.workercluster import WorkerCluster
from primazactl.primazamain.maincluster import MainCluster
from primazactl.primazamain.constants import DEFAULT_TENANT
from primazactl.version import __primaza_version__
from .constants import SERVICE, APPLICATION
from primazactl.utils.kubeconfig import from_env


def add_args_namespace(parser: argparse.ArgumentParser, type):
    parser.add_argument(
        "namespace",
        type=kubernetes_name,
        help="namespace to create")

    parser.add_argument(
        "-d", "--cluster-environment",
        dest="cluster_environment",
        type=kubernetes_name,
        required=True,
        help="name to use for the ClusterEnvironment that \
                will be created in Primaza")

    parser.add_argument(
        "-c", "--context",
        dest="context",
        type=str,
        required=False,
        help="name of cluster, as it appears in kubeconfig, "
             "on which to create the service or application namespace, "
             "default: current kubeconfig context",
        default=None)

    parser.add_argument(
        "-m", "--tenant-context",
        dest="tenant_context",
        required=False,
        help="name of cluster, as it appears in kubeconfig, \
                on which Primaza tenant was created. Default: \
                current kubeconfig context",
        type=str,
        default=None)

    parser.add_argument(
        "-f", "--config",
        dest="config",
        type=existing_file,
        required=False,
        help="Config file containing agent roles")

    parser.add_argument(
        "-t", "--tenant",
        dest="tenant",
        type=kubernetes_name,
        required=False,
        help=f"tenant to use. Default: {DEFAULT_TENANT}",
        default=DEFAULT_TENANT)

    parser.add_argument(
        "-v", "--version",
        dest="version",
        required=False,
        help=f"Version of primaza to use, default: {__primaza_version__}. "
             "Ignored if --config is set.",
        type=semvertag_or_latest,
        default=__primaza_version__)

    parser.add_argument(
        "-k", "--kubeconfig",
        dest="kubeconfig",
        required=False,
        help=f"path to kubeconfig file, default: KUBECONFIG \
                   environment variable if set, otherwise \
                   {(os.path.join(Path.home(),'.kube','config'))}",
        type=existing_file,
        default=from_env())

    parser.add_argument(
        "-l", "--tenant-kubeconfig",
        dest="tenant_kubeconfig",
        required=False,
        help=f"path to kubeconfig file for the tenant, default: KUBECONFIG \
                   environment variable if set, otherwise \
                   {(os.path.join(Path.home(),'.kube','config'))}",
        type=existing_file,
        default=from_env())


def __create_namespace(args, type):
    try:

        main = MainCluster(context=args.tenant_context,
                           namespace=args.tenant,
                           kubeconfig_path=args.tenant_kubeconfig,
                           config_file=None,
                           version=None,)

        worker = WorkerCluster(
            primaza_main=main,
            context=args.context,
            kubeconfig_file=args.kubeconfig,
            config_file=None,
            version=None,
            environment=None,
            cluster_environment=args.cluster_environment,
            tenant=args.tenant,
        )

        main_user = main.create_primaza_identity(
            args.cluster_environment)
        kcfg = main.get_kubeconfig(main_user, args.context)

        namespace = WorkerNamespace(type,
                                    args.namespace,
                                    args.cluster_environment,
                                    args.context,
                                    args.kubeconfig,
                                    args.config,
                                    args.version,
                                    main,
                                    worker)
        namespace.create()

        worker.create_namespaced_kubeconfig_secret(kcfg, args.tenant)

        namespace.check()
        print(f"{type} namespace primaza-{type} was successfully created")

    except Exception as e:
        print(traceback.format_exc())
        print(f"\nAn exception creating an {type} namespace",
              file=sys.stderr)
        raise e


def create_application_namespace(args):
    __create_namespace(args, APPLICATION)


def create_service_namespace(args):
    __create_namespace(args, SERVICE)
