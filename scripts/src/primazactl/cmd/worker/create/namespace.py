import argparse
import traceback
import sys
from primazactl.types import kubernetes_name, existing_file
from primazactl.primazaworker.workernamespace import WorkerNamespace
from primazactl.primazaworker.workercluster import WorkerCluster
from primazactl.primazaworker.constants import WORKER_ID
from primazactl.primazamain.maincluster import MainCluster
from .constants import SERVICE, APPLICATION


def add_create_applications_namespace(parser: argparse.ArgumentParser,
                                      parents=[]):
    applications_namespace_parser = parser.add_parser(
        f"{APPLICATION}-namespace",
        help="Create a namespace for applications",
        parents=parents)
    applications_namespace_parser.set_defaults(
        func=create_application_namespace)
    add_args_namespace(applications_namespace_parser)


def add_create_services_namespace(parser: argparse.ArgumentParser,
                                  parents=[]):
    services_namespace_parser = parser.add_parser(
        f"{SERVICE}-namespace",
        help="Create a namespace for services",
        parents=parents)
    services_namespace_parser.set_defaults(func=create_service_namespace)
    add_args_namespace(services_namespace_parser)


def add_args_namespace(parser: argparse.ArgumentParser):

    parser.add_argument(
        "-d", "--clusterenvironment",
        dest="cluster_environment",
        type=kubernetes_name,
        required=True,
        help="name to use for the ClusterEnvironment that \
                will be created in Primaza")

    parser.add_argument(
        "-c", "--clustername",
        dest="cluster_name",
        type=str,
        required=False,
        help="name of worker cluster, as it appears in kubeconfig, \
                  on which to create the namespace, default: \
                  current kubeconfig context",
        default=None)

    parser.add_argument(
        "-m", "--primaza-clustername",
        dest="main_clustername",
        required=False,
        help="name of cluster, as it appears in kubeconfig, \
                on which Primaza is installed. Default: \
                current kubeconfig context",
        type=str,
        default=None)

    parser.add_argument(
        "-f", "--config",
        dest="config",
        type=existing_file,
        required=False,
        help="Config file containing agent roles")


def __create_namespace(args, type):
    try:

        main = MainCluster(cluster_name=args.main_clustername,
                           kubeconfig_path=None,
                           config_file=None,
                           version=None,)

        worker = WorkerCluster(
            primaza_main=main,
            cluster_name=args.cluster_name,
            kubeconfig_file=None,
            config_file=None,
            version=None,
            environment=None,
            cluster_environment=args.cluster_environment,
        )

        main_user = main.create_primaza_identity(
            args.cluster_environment)
        kcfg = main.get_kubeconfig(main_user, args.cluster_name)

        namespace = WorkerNamespace(type,
                                    f"primaza-{type}",
                                    args.cluster_environment,
                                    args.cluster_name,
                                    args.config,
                                    main,
                                    worker)
        namespace.create()

        secret_name = f"{WORKER_ID}-{args.cluster_environment}"
        worker.create_namespaced_secret(secret_name, kcfg)

        namespace.check()
        print(f"{type} namespace primaza-{type} was successfully created")

    except Exception:
        print(traceback.format_exc())
        print(f"\nAn exception creating an {type} namespace",
              file=sys.stderr)


def create_application_namespace(args):
    __create_namespace(args, APPLICATION)


def create_service_namespace(args):
    __create_namespace(args, SERVICE)
