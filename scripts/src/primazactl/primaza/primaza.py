import yaml
from typing import Dict
from primazactl.utils import logger, command
from primazactl.identity import kubeidentity
from primazactl.kube.secret import Secret
from primazactl.utils import kubeconfig
from primazactl.utils.kubeconfigwrapper import KubeConfigWrapper


class Primaza(object):

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
        out, err = command.Command().run(f"docker inspect {control_plane}")
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

    def get_kubeconfig(self, id: str, other_cluster_name) -> Dict:
        logger.log_entry(f"id: {id}, "
                         f"other_cluster_name: {other_cluster_name}")
        server_url = self.get_updated_server_url() \
            if self.cluster_name != other_cluster_name \
            else None

        return kubeidentity.get_identity_kubeconfig(
            self.kubeconfig,
            id,
            self.namespace,
            server_url)

    def create_service_account(self, user: str = None):
        logger.log_entry()
        if user:
            self.user = user
        api_client = self.kubeconfig.get_api_client()
        kubeidentity.create_identity(api_client, self.namespace, self.user)

    def create_clustercontext_secret(self, secret_name: str, kubeconfig: str):
        """
        Creates the Primaza's ClusterContext secret
        """
        logger.log_entry(f"secret_name: {secret_name}, "
                         f"namespace: {self.namespace}")
        api_client = self.kubeconfig.get_api_client()
        secret = Secret(api_client, secret_name,
                        self.namespace, kubeconfig)
        secret.create()

    def kubeconfig(self) -> KubeConfigWrapper:
        return KubeConfigWrapper(self.cluster_name, self.kube_config_file)
