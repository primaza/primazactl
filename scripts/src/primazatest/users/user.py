import yaml
import argparse
import os
from kubernetes.client.rest import ApiException
from kubernetes import client
from primazactl.identity.kubeidentity import KubeIdentity
from primazactl.kubectl.apply import apply_resource
from primazactl.utils import logger
from primazactl.utils.kubeconfigwrapper import KubeConfigWrapper
from primazactl.utils import kubeconfig
import inspect
from pathlib import Path


TENANT: str = "tenant"
TENANT_BAD: str = "tenant-bad"
WORKER: str = "worker"
WORKER_BAD: str = "worker-bad"
APP: str = "application-agent"
APP_BAD: str = "application-agent-bad"
SVC: str = "service-agent"
SVC_BAD: str = "service-agent-bad"


class User(object):

    user_config_file: str = None
    api_client: client = None
    user_name: str = None
    cluster_name: str = None
    user_identity: KubeIdentity = None
    certificate_private_key: bytes = None
    certificate: str = None

    def __init__(self, user_config_file, api_client, cluster_name):
        self.user_config_file = user_config_file
        self.api_client = api_client
        self.cluster_name = cluster_name

    def read_config(self):
        logger.log_entry(f"process file: {self.user_config_file}")

        with open(self.user_config_file, 'r') as manifest:
            resources = yaml.safe_load_all(manifest)
            resource_list = list(resources)

        for resource in resource_list:
            logger.log_info(f"process resource: {resource}")
            if resource["kind"] == "ServiceAccount":
                namespace = resource["metadata"]["namespace"]
                self.user_name = resource["metadata"]["name"]
                logger.log_info("found service account, "
                                f"name: {self.user_name}")
                logger.log_info("found service account, "
                                f"namespace: {namespace}")
                self.user_identity = KubeIdentity(self.api_client,
                                                  self.user_name,
                                                  f"{self.user_name}-key",
                                                  namespace,
                                                  self.user_name)

                self.user_identity.create()
            else:
                try:
                    _, error = apply_resource(resource,
                                              self.api_client,
                                              "delete")
                except ApiException as api_exception:
                    body = yaml.safe_load(api_exception.body)
                    if body["reason"] == "NotFound":
                        logger.log_info(f'create: {body["message"]}')
                        pass
                    else:
                        logger.log_error(api_exception)
                        raise api_exception

                try:
                    _, error = apply_resource(resource,
                                              self.api_client,
                                              "create")
                except ApiException as api_exception:
                    body = yaml.safe_load(api_exception.body)
                    if body["reason"] == "AlreadyExists":
                        logger.log_info(f'create: {body["message"]}')
                        pass
                    else:
                        logger.log_error(api_exception)
                        raise api_exception

    def write_kubeconfig(self, new_file_path, kube_config):

        logger.log_entry(f"new file path {new_file_path}")

        kcd = kube_config.get_kube_config_content_as_yaml()
        kcd["contexts"][0]["context"]["user"] = self.user_name
        if self.user_identity:
            idauth = self.user_identity.get_token()
            new_user = {"user": {"token": idauth["token"]},
                        "name": self.user_name}
            kcd["users"][0] = new_user

        os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
        with open(new_file_path, "w") as file:
            file.write(yaml.dump(kcd))
            logger.log_info("Write complete")
            print(f"kubeconfig file created for user {self.user_name} : "
                  f"{new_file_path}")


def get_my_dir():
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    file_path = Path(os.path.abspath(filename))
    my_dir = ""
    prev_dir = ""
    for dir in file_path.parts:
        if prev_dir == "primazactl" and dir in ["out", "scripts"]:
            break
        prev_dir = dir
        my_dir = os.path.join(my_dir, dir)
    return os.path.join(my_dir, "scripts/src/primazatest/users")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("type", type=str,
                        choices=[TENANT, WORKER, APP, SVC, TENANT_BAD,
                                 WORKER_BAD, APP_BAD, SVC_BAD],
                        help='type of user to create.')
    parser.add_argument("-c", "--cluster_name",
                        dest="cluster_name",
                        help="cluster name",
                        required=True)
    parser.add_argument("-f", "--config_file",
                        dest="config_file",
                        help="file with user account definition",
                        required=False)
    parser.add_argument("-o", "--output_dir",
                        dest="output_dir",
                        help="directory to output updated kubeconfig",
                        required=False)
    parser.add_argument("-x", "--verbose",
                        dest="verbose",
                        required=False,
                        action="count",
                        help="Set for verbose output")

    args = parser.parse_args()

    if hasattr(args, "verbose"):
        logger.set_verbose(args.verbose)

    if args.output_dir:
        output_file = os.path.join(args.output_dir,
                                   f"{args.type}-kube.config")
    else:
        output_file = f"./out/users/{args.type}-kube.config"

    if args.config_file:
        config_file = args.config_file
    else:
        config_file = os.path.join(get_my_dir(), f"config/{args.type}.yaml")

    kcw = KubeConfigWrapper(args.cluster_name, kubeconfig.from_env())
    kcw = kcw.get_kube_config_for_cluster()
    user = User(config_file,
                kcw.get_api_client(),
                args.cluster_name)
    user.read_config()
    user.write_kubeconfig(output_file, kcw)


if __name__ == "__main__":
    main()
