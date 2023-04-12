import yaml
from typing import Dict, Tuple
from primazactl.utils import logger
from primazactl.utils.command import Command
from primazactl.identity.kubeidentity import KubeIdentity
from primazactl.kube.secret import Secret
from primazactl.kube.role import Role
from primazactl.kube.access.accessreview import AccessReview
from primazactl.utils import kubeconfig
from primazactl.utils.kubeconfigwrapper import KubeConfigWrapper


class PrimazaCluster(object):

    namespace: str = None
    cluster_name: str = None
    user: str = None
    kube_config_file: str = None
    kubeconfig: KubeConfigWrapper = None

    def __init__(self, namespace, cluster_name, user, kubeconfig_path):
        self.namespace = namespace
        self.cluster_name = cluster_name
        self.user = user

        self.kube_config_file = kubeconfig_path \
            if kubeconfig_path is not None \
            else kubeconfig.from_env()

        kcw = KubeConfigWrapper(cluster_name, self.kube_config_file)
        self.kubeconfig = kcw.get_kube_config_for_cluster()

    def get_updated_server_url(self):
        logger.log_entry()
        cluster = f'{self.cluster_name.replace("kind-","")}'
        control_plane = f'{cluster}-control-plane'
        out, err = Command().run(f"docker inspect {control_plane}")
        if err != 0:
            raise RuntimeError("\n[ERROR] error getting data from docker:"
                               f"{control_plane} : {err}")

        docker_data = yaml.safe_load(out)
        try:
            networks = docker_data[0]["NetworkSettings"]["Networks"]
            ipaddr = networks["kind"]["IPAddress"]
            logger.log_info(f"new cluster url: https://{ipaddr}:6443")
            return f"https://{ipaddr}:6443"
        except KeyError:
            logger.log_info("new cluster url not found")
            return ""

    def get_kubeconfig(self, identity: KubeIdentity,
                       other_cluster_name) -> Dict:
        logger.log_entry(f"id: {identity.identity}, "
                         f"other_cluster_name: {other_cluster_name}")
        server_url = self.get_updated_server_url() \
            if self.cluster_name != other_cluster_name \
            else None

        return identity.get_kubeconfig(self.kubeconfig, server_url)

    def create_identity(self, user: str = None) -> KubeIdentity:
        logger.log_entry()
        if user:
            self.user = user
        api_client = self.kubeconfig.get_api_client()
        identity = KubeIdentity(api_client, self.user, self.namespace)
        identity.create()
        return identity

    def create_namespaced_secret(self, secret_name: str, kubeconfig: str):
        """
        Creates the Primaza's secret
        """
        logger.log_entry(f"secret_name: {secret_name}, "
                         f"namespace: {self.namespace}")
        api_client = self.kubeconfig.get_api_client()
        secret = Secret(api_client, secret_name,
                        self.namespace, kubeconfig)
        secret.create()

    def kubeconfig(self) -> KubeConfigWrapper:
        return KubeConfigWrapper(self.cluster_name, self.kube_config_file)

    def kubectl_do(self, cmd: str) -> Tuple[str, int]:
        return Command().run(
            "kubectl"
            f" --kubeconfig {self.kube_config_file}"
            f" --context {self.cluster_name}"
            f" {cmd}")

    def check_service_account_roles(self, service_account_name,
                                    role_name, role_namespace):
        logger.log_entry(self.namespace)
        api_client = self.kubeconfig.get_api_client()
        ar = AccessReview(api_client,
                          service_account_name,
                          self.namespace,
                          role_namespace)
        role = Role(api_client,
                    role_name, role_namespace, None)
        rules = role.get_rules()
        error_messages = []
        for rule in rules:
            error_message = ar.check_access(rule)
            if error_message:
                error_messages.extend(error_message)
        return error_messages
