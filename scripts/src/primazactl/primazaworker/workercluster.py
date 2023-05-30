from kubernetes import client
from primazactl.utils.kubeconfigwrapper import KubeConfigWrapper
from primazactl.utils import logger
from primazactl.primazamain.maincluster import MainCluster
from .constants import WORKER_NAMESPACE, WORKER_ID
from primazactl.primaza.primazacluster import PrimazaCluster
from primazactl.utils import names
from primazactl.kubectl.manifest import Manifest
from primazactl.kubectl.constants import WORKER_CONFIG


class WorkerCluster(PrimazaCluster):
    kube_config_file: str = None
    kubeconfig: KubeConfigWrapper = None
    config_file: str = None
    version: str = None
    environment: str = None
    cluster_environment: str = None
    primaza_main: MainCluster = None
    manifest: Manifest = None

    def __init__(
            self,
            primaza_main: MainCluster,
            context: str,
            kubeconfig_file: str,
            config_file: str,
            version: str,
            environment: str,
            cluster_environment: str,
            tenant: str,
            ):

        super().__init__(WORKER_NAMESPACE,
                         context,
                         WORKER_ID,
                         cluster_environment,
                         kubeconfig_file,
                         config_file,
                         cluster_environment,
                         tenant)

        self.primaza_main = primaza_main
        self.environment = environment
        self.version = version
        self.manifest = Manifest(WORKER_NAMESPACE, config_file,
                                 version, WORKER_CONFIG)

        kcw = KubeConfigWrapper(context, self.kube_config_file)
        self.kubeconfig = kcw.get_kube_config_for_cluster()

        logger.log_info("WorkerCluster created for cluster "
                        f"{self.context}, config_file: "
                        f"{self.config_file}")

    def install_worker(self):
        logger.log_entry()
        # need an agnostic way to get the kubeconfig - get as a parameter

        api_client = self.kubeconfig.get_api_client()
        corev1 = client.CoreV1Api(api_client)
        api_response = corev1.list_namespace()
        for item in api_response.items:
            logger.log_info(f"Namespace: {item.metadata.name} is "
                            f"make lint{item.status.phase}")

        if not self.context:
            self.context = self.kubeconfig.context
            if not self.context:
                raise RuntimeError("\n[ERROR] installing priamza: "
                                   "no cluster found.")
            else:
                logger.log_info("Cluster set to current context: "
                                f"{self.context}")

        self.install_crd()

        logger.log_info("Create certificate signing request")

        sa_name, key_name = names.get_identity_names(self.cluster_environment,
                                                     self.namespace)

        identity = self.create_identity(sa_name, key_name)

        logger.log_info("Create cluster context secret in main")
        cc_kubeconfig = self.get_kubeconfig(identity,
                                            self.primaza_main.context)
        secret_name = self.primaza_main.create_namespaced_kubeconfig_secret(
            cc_kubeconfig, self.primaza_main.namespace,
            self.cluster_environment)

        logger.log_info("Create cluster environment in main")

        ce = self.primaza_main.create_cluster_environment(
            self.cluster_environment, self.environment, secret_name)
        ce.check("Online", "Online", "True")

        logger.log_exit("Worker install complete")

    def install_crd(self):
        logger.log_entry(f"config: {self.config_file}")
        self.install_config(self.manifest)

    def check_worker_roles(self, role_name, role_namespace):
        return self.check_service_account_roles(self.user,
                                                role_name,
                                                role_namespace)
