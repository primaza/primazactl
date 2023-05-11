from primazactl.utils import logger
from primazactl.utils import names
from primazactl.kube.namespace import Namespace
from primazactl.kube.role import Role
from primazactl.kube.rolebinding import RoleBinding
from primazactl.kube.roles.primazaroles import get_primaza_namespace_role
from primazactl.primaza.primazacluster import PrimazaCluster
from primazactl.primazamain.maincluster import MainCluster
from primazactl.cmd.worker.create.constants import APPLICATION
from primazactl.kubectl.manifest import Manifest
from primazactl.kubectl.constants import APP_AGENT_CONFIG, SVC_AGENT_CONFIG

from .workercluster import WorkerCluster


class WorkerNamespace(PrimazaCluster):

    main_cluster: str = None
    type: str = None
    user_type: str = None
    kube_namespace: Namespace = None
    main: MainCluster = None
    worker: WorkerCluster = None
    secret_name: str = None
    secret_cfg: str = None
    manifest: Manifest = None

    def __init__(self, type,
                 namespace,
                 cluster_environment,
                 worker_cluster,
                 role_config,
                 version,
                 main,
                 worker):

        self.type = type
        self.user_type = names.USER_TYPE_APP \
            if self.type == APPLICATION \
            else names.USER_TYPE_SVC

        super().__init__(namespace,
                         worker_cluster,
                         f"primaza-{self.type}-agent",
                         self.user_type,
                         None,
                         role_config,
                         cluster_environment)

        self.main = main
        self.worker = worker

        manifest_type = APP_AGENT_CONFIG \
            if self.type == APPLICATION \
            else SVC_AGENT_CONFIG

        self.manifest = Manifest(namespace, role_config,
                                 version, manifest_type)

        api_client = self.kubeconfig.get_api_client()
        self.kube_namespace = Namespace(api_client, namespace)

    def create(self):
        logger.log_entry(f"namespace type: {self.type}, "
                         f"cluster environment: {self.cluster_environment}, "
                         f"worker cluster: {self.worker.cluster_name}")

        # On worker cluster
        # - create the namespace
        self.kube_namespace.create()

        # Request a new service account from primaza main
        main_identity = self.main.create_primaza_identity(
            self.cluster_environment,
            self.user_type,
            self.namespace)

        # Get kubeconfig with secret from service accounf
        kc = self.main.get_kubeconfig(main_identity, self.cluster_name)

        # - in the created namespace, create the Secret
        #     'primaza-auth-$CLUSTER_ENVIRONMENT' the Worker key
        #     and the kubeconfig for authenticating with the Primaza cluster.

        self.create_namespaced_kubeconfig_secret(kc)

        # - In the created namespace, create the Role for the
        #   agent (named for example primaza-application-agent or
        #   primaza-service-agent), that will grant it access to
        #   namespace and its resources
        # - In the created namespace, create a RoleBinding for binding
        #   the agents' Service Account to the role defined above
        self.install_config(self.manifest)

        # - In the created namespace, create a Role (named
        #   primaza-application or primaza-service), that will grant
        #   primaza access to namespace and its resources
        #   (e.g. create ServiceClaim, create RegisteredServices)
        api_client = self.kubeconfig.get_api_client()
        role = names.get_role_name(self.user_type)
        primaza_policy = get_primaza_namespace_role(role,
                                                    self.namespace)
        primaza_role = Role(api_client, primaza_policy.metadata.name,
                            self.namespace, primaza_policy)
        primaza_role.create()

        # - In the created namespace, RoleBinding for binding the user primaza
        #   to the role defined above
        rolebinding = names.get_rolebinding_name(self.user_type)
        primaza_binding = RoleBinding(api_client,
                                      rolebinding,
                                      self.namespace,
                                      primaza_role.name,
                                      self.worker.namespace,
                                      self.worker.user)
        primaza_binding.create()

        ce = self.main.get_cluster_environment()
        ce.add_namespace(self.type, self.namespace)
        logger.log_info(f"ce:{ce.body}")

    def check(self):
        logger.log_entry(f"Cluster: {self.cluster_name}, "
                         f"Namespace {self.namespace}")

        error_messages = []
        if self.type == APPLICATION:
            error_message = self.check_service_account_roles(
                "primaza-app-agent",
                "primaza:app:leader-election", self.namespace)
            if error_message:
                error_messages.extend(error_message)

            error_message = self.check_service_account_roles(
                    "primaza-app-agent",
                    "primaza:app:manager", self.namespace)
            if error_message:
                error_messages.extend(error_message)

            error_message = self.worker.check_worker_roles(
                names.get_rolebinding_name(self.user_type),
                self.namespace)
            if error_message:
                error_messages.extend(error_message)

        else:
            error_message = self.check_service_account_roles(
                "primaza-svc-agent",
                "primaza:svc:leader-election", self.namespace)
            if error_message:
                error_messages.extend(error_message)

            error_message = self.check_service_account_roles(
                "primaza-svc-agent",
                "primaza:svc:manager", self.namespace)
            if error_message:
                error_messages.extend(error_message)

            error_message = self.worker.check_worker_roles(
                names.get_rolebinding_name(self.user_type), self.namespace)
            if error_message:
                error_messages.extend(error_message)

        if error_messages:
            raise RuntimeError(
                "Error: namespace install has failed to created the correct "
                f"accesses. Error messages were: {error_messages}")

        ce = self.main.get_cluster_environment()
        ce.check("Online", "Online", "True")

        logger.log_exit("All checks passed")
