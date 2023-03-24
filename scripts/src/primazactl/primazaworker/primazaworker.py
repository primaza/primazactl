import yaml
from typing import Dict
from kubernetes import client
from primazactl.utils.kubeconfigwrapper import KubeConfigWrapper
from primazactl.identity import kubeidentity
from primazactl.utils import logger, command
from primazactl.utils.primazaconfig import PrimazaConfig
from primazactl.primazamain.primazamain import PrimazaMain


class PrimazaWorker(object):
    cluster_name: str = None
    kube_config_file: str = None
    kubeconfig: KubeConfigWrapper = None
    config_file: str = None
    version: str = None
    environment: str = None
    cluster_environment: str = None
    primaza_main: PrimazaMain = None

    def __init__(
        self,
        primaza_main: PrimazaMain,
        cluster_name: str,
        kubeconfig_file: str,
        config_file: str,
        version: str,
        environment: str,
        cluster_environment: str,
    ):
        self.primaza_main = primaza_main
        self.cluster_name = cluster_name
        self.config_file = config_file
        self.environment = environment
        self.cluster_environment = cluster_environment
        self.version = version

        kcw = KubeConfigWrapper(cluster_name, kubeconfig_file)
        self.kubeconfig = kcw.get_kube_config_for_cluster()

        logger.log_info("PrimazaWorker created for cluster "
                        f"{self.cluster_name}")

    def create_primaza_service_account(self):
        namespace = "kube-system"
        id = "primaza"

        api_client = self.kubeconfig.get_api_client()
        kubeidentity.create_identity(api_client, namespace, id)

    def get_kubeconfig(self, id: str) -> Dict:
        serverUrl = self.get_updated_server_url()\
            if self.cluster_name != self.primaza_main.cluster_name \
            else None

        return kubeidentity.get_identity_kubeconfig(
            self.kubeconfig,
            id,
            serverUrl)

    def get_updated_server_url(self):
        logger.log_entry()
        cluster = f'{self.cluster_name.replace("kind-","")}'
        control_plane = f'{cluster}-control-plane'
        out, err = command.Command().run(f"docker inspect {control_plane}")
        if err != 0:
            raise RuntimeError("\n[ERROR] error getting data from docker:"
                               f"{self.cluster_name}-control-plane : {err}")

        docker_data = yaml.safe_load(out)
        try:
            networks = docker_data[0]["NetworkSettings"]["Networks"]
            ipaddr = networks["kind"]["IPAddress"]
            logger.log_info(f"new worker url: https://{ipaddr}:6443")
            return f"https://{ipaddr}:6443"
        except KeyError:
            logger.log_info("new worker url not found")
            return ""

    def install_worker(self):
        logger.log_entry()
        # need an agnostic way to get the kubeconfig - get as a parameter

        api_client = self.kubeconfig.get_api_client()
        corev1 = client.CoreV1Api(api_client)
        api_response = corev1.list_namespace()
        for item in api_response.items:
            print(f"Namespace: {item.metadata.name} is {item.status.phase}")

        if not self.cluster_name:
            self.cluster_name = self.kubeconfig.get_cluster_name()
            if not self.cluster_name:
                raise RuntimeError("\n[ERROR] installing priamza: "
                                   "no cluster found.")
            else:
                logger.log_info("Cluster set to current context: "
                                f"{self.cluster_name}")

        self.install_crd()

        logger.log_info("Create certificate signing request")
        self.create_primaza_service_account()

        logger.log_info("Create cluster context secret in main")
        secret_name = f"primaza-{self.cluster_environment}-kubeconfig"
        cc_kubeconfig = self.get_kubeconfig("primaza")
        self.primaza_main.create_clustercontext_secret(
            secret_name, cc_kubeconfig)

        logger.log_info("Create cluster environment in main")
        self.primaza_main.write_cluster_environment(
            self.cluster_environment, self.environment, secret_name)

        self.primaza_main.check_state(
            self.cluster_environment, "Online")
        self.primaza_main.check_status_condition(
            self.cluster_environment, "Online", "True")
        self.primaza_main.check_status_condition(
            self.cluster_environment,
            "ApplicationNamespacePermissionsRequired",
            "False")
        self.primaza_main.check_status_condition(
            self.cluster_environment,
            "ServiceNamespacePermissionsRequired",
            "False")

        logger.log_exit("Worker install complete")

    def install_crd(self):
        logger.log_entry()

        config = PrimazaConfig("worker",
                               self.config_file,
                               self.version)

        err = config.apply(self.kubeconfig)
        if err != 0:
            raise RuntimeError("error deploying Primaza's CRDs into "
                               f"cluster {self.cluster_name} : {err}\n")
