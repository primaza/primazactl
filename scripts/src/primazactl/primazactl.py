import argparse
import os
import semver
import sys
from pathlib import Path
from primazactl.primazamain import primazamain
sys.path.append('./scripts/src/')


def main():

    parser = argparse.ArgumentParser(
        prog='primazactl',
        description='Configure and install primaza and primaza worker \
                    on clusters',
        epilog="Brought to you by the RedHat app-services team.")
    parser.add_argument("action", type=str,
                        choices=["install", "info", "uninstall", "join"],
                        help='type of action to perform.')
    parser.add_argument('install_type', type=str,
                        choices=["main", "worker"],
                        help='specify primaza or worker.')
    parser.add_argument("-c", "--clustername",
                        dest="cluster_name", type=str, required=False,
                        help="name of cluster, as it appears in kubeconfig, \
                             on which to install primaza or worker, default: \
                             current kubeconfig context")
    parser.add_argument("-k", "--kubeconfig",
                        dest="kubeconfig", type=str, required=False,
                        help=f"path to kubeconfig file, default: KUBECONFIG \
                               environment variable if set, otherwise \
                               {(os.path.join(Path.home(),'.kube','config'))}")
    parser.add_argument("-f", "--config",
                        dest="primaza_config", type=str, required=False,
                        help="primaza config file. Takes precedence \
                        over --version")
    parser.add_argument("-v", "--version",
                        dest="primaza_version", type=str, required=False,
                        help="Version of primaza to use, default: newest \
                              release available. Ignored if --config is set.")

    args = parser.parse_args()

    cluster_name = args.cluster_name

    kube_config = args.kubeconfig
    if not kube_config:
        kube_config = os.environ.get("KUBECONFIG")
        if not kube_config:
            kube_config = str(os.path.join(Path.home(), ".kube", "config"))

    if not os.path.isfile(kube_config):
        parser.error("\n[ERROR] --kubeconfig does not specify a valid file: "
                     f"{kube_config}\n")

    primaza_config = args.primaza_config
    primaza_version = args.primaza_version
    if primaza_config:
        primaza_version = None
        if args.action == "install" and args.install_type == "main":
            if not os.path.isfile(primaza_config):
                parser.error("\n[ERROR] --config does not specify a valid"
                             f" file: {primaza_config}\n")

    elif primaza_version:
        if not semver.VersionInfo.isvalid(primaza_version):
            parser.error("\n[ERROR] --version is not a valid semantic "
                         f"version: {primaza_version}\n")

    print(f'install_type: {args.install_type}')
    print(f'primaza_config: {primaza_config}')
    print(f'primaza version: {primaza_version}')
    print(f'cluster name: {cluster_name}')
    print(f'kube config: {kube_config}')

    if args.action == "install":

        if args.install_type == "worker":
            parser.error("Install and configure primaza worker \
                   is not yet implemented")
        else:
            print("Install and configure primaza main is in progress")
            try:
                pmain = primazamain.PrimazaMain(cluster_name,
                                                kube_config,
                                                primaza_config,
                                                primaza_version)
                pmain.install_primaza()
            except Exception as err:
                if cluster_name:
                    parser.error("[ERROR] installing main on "
                                 f"{cluster_name}: {err}")
                else:
                    parser.error(f"[ERROR] installing main: {err}")

    else:
        parser.error("info, uninstall and join are not yet implemented.")


if __name__ == "__main__":
    main()
