
from primazactl.utils import logger
from primazactl.utils.kubeconfigwrapper import KubeConfigWrapper
from .constants import PRIMAZA_NAMESPACE, PRIMAZA_USER
from primazactl.primaza.primazacluster import PrimazaCluster
from primazactl.identity.kubeidentity import KubeIdentity
from .clusterenvironment import ClusterEnvironment
from primazactl.utils import names


class MainCluster(PrimazaCluster):
    kubeconfig: KubeConfigWrapper = None
    kube_config_file: str
    primaza_version: str | None = None

    def __init__(
            self,
            cluster_name: str | None,
            namespace: str | None,
            kubeconfig_path: str | None,
            config_file: str | None,
            version: str | None):

        if not namespace:
            namespace = PRIMAZA_NAMESPACE

        cluster_name = cluster_name \
            if cluster_name is not None \
            else KubeConfigWrapper(None, self.kube_config_file).get_context()

        super().__init__(namespace,
                         cluster_name,
                         PRIMAZA_USER,
                         None,
                         kubeconfig_path,
                         config_file,
                         None)

        self.primaza_version = version

        kcw = KubeConfigWrapper(cluster_name, self.kube_config_file)
        self.kubeconfig = kcw.get_kube_config_for_cluster()

        logger.log_info("Primaza main created for cluster "
                        f"{self.cluster_name}")

    def install_primaza(self):
        try:
            self.install_config()
        except Exception as exc:
            raise RuntimeError(
                "error deploying Primaza's controller into "
                f"cluster {self.cluster_name} : {exc}")

    def create_primaza_identity(self, cluster_environment: str,
                                user_type: str = None,
                                namespace: str = None) -> KubeIdentity:
        logger.log_entry(f"type: cluster environment: {cluster_environment}")
        if not namespace:
            namespace = self.namespace
        logger.log_info(f"User: {user_type}, namespace: {namespace}")
        sa_name, key_name = names.get_identity_names(cluster_environment,
                                                     namespace,
                                                     user_type)

        return self.create_identity(sa_name, key_name)

    def create_cluster_environment(self,
                                   cluster_environment_name,
                                   environment_name,
                                   secret_name) -> ClusterEnvironment:

        logger.log_entry("kind: ClusterEnvironment, "
                         f"name: {cluster_environment_name}, "
                         f"environment_name: {environment_name} "
                         f"secret_name: {secret_name}")

        ce = ClusterEnvironment(self.kubeconfig.get_api_client(),
                                self.namespace,
                                cluster_environment_name,
                                environment_name,
                                secret_name)
        ce.create()
        return ce

    def get_cluster_environment(self) -> ClusterEnvironment:
        ce = ClusterEnvironment(self.kubeconfig.get_api_client(),
                                self.namespace)
        ce.find()
        return ce

    def uninstall_primaza(self):
        self.uninstall_config()
