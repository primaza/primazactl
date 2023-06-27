from primazactl.utils import logger
from primazactl.utils.kubeconfigwrapper import KubeConfigWrapper
from .constants import PRIMAZA_USER
from primazactl.primaza.primazacluster import PrimazaCluster
from primazactl.identity.kubeidentity import KubeIdentity
from .clusterenvironment import ClusterEnvironment
from primazactl.utils import names
from primazactl.kubectl.manifest import Manifest
from primazactl.kubectl.constants import PRIMAZA_CONFIG


class MainCluster(PrimazaCluster):
    kubeconfig: KubeConfigWrapper = None
    kube_config_file: str
    primaza_version: str | None = None
    manifest: Manifest = None

    def __init__(
            self,
            context: str | None,
            namespace: str | None,
            kubeconfig_path: str | None,
            config_file: str | None,
            version: str | None):

        self.kube_config_file = kubeconfig_path

        context = context \
            if context is not None \
            else KubeConfigWrapper(None, self.kube_config_file).get_context()

        super().__init__(namespace,
                         context,
                         PRIMAZA_USER,
                         None,
                         kubeconfig_path,
                         config_file,
                         None,
                         namespace)

        self.primaza_version = version

        self.manifest = Manifest(namespace, config_file,
                                 version, PRIMAZA_CONFIG)

        kcw = KubeConfigWrapper(context, self.kube_config_file)
        self.kubeconfig = kcw.get_kube_config_for_cluster()

        logger.log_info("Primaza main created for cluster "
                        f"{self.context}")

    def install_primaza(self):
        self.install_config(self.manifest)

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

    def get_cluster_environment(self, name) -> ClusterEnvironment:
        ce = ClusterEnvironment(
                api_client=self.kubeconfig.get_api_client(),
                namespace=self.namespace,
                name=name)
        ce.find()
        return ce

    def uninstall_primaza(self):
        self.uninstall_config(self.manifest)
