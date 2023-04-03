from primazactl.utils import logger
from primazactl.kube.namespace import Namespace
from primazactl.kube.serviceaccount import ServiceAccount
from primazactl.kube.role import Role
from primazactl.kube.secret import Secret
from primazactl.kube.rolebinding import RoleBinding
from primazactl.kube.roles.primazaroles import get_primaza_namespace_role
from primazactl.cmd.worker.create.constants import APPLICATION
from primazactl.primaza.primazacluster import PrimazaCluster


class WorkerNamespace(PrimazaCluster):

    main_cluster: str = None
    type: str = None
    kube_namesapce: Namespace = None
    cluster_environment: str = None
    role_config: str = None
    main_user: str = None
    secret_cfg: str = None

    def __init__(self, type,
                 namespace,
                 cluster_environment,
                 worker_cluster,
                 main_cluster,
                 role_config,
                 main_user,
                 secret_kcfg):

        super().__init__(namespace,
                         worker_cluster,
                         f"primaza-{self.type}-agent",
                         None)

        self.type = type
        self.main_cluster = main_cluster
        api_client = self.kubeconfig.get_api_client()
        self.cluster_environment = cluster_environment
        self.kube_namespace = Namespace(api_client, namespace)
        self.role_config = role_config
        self.main_user = main_user
        self.secret_cfg = secret_kcfg

    def create(self):
        logger.log_entry(f"namespace type: {self.type}, "
                         f"cluster environment: {self.cluster_environment}, "
                         f"worker cluster: {self.cluster_name}, "
                         f"main_cluster: {self.main_cluster}")

        # On worker cluster
        # - create the namespace
        self.kube_namespace.create()

        # - in the created namespace, create the Secret
        #     'primaza-auth-$CLUSTER_ENVIRONMENT' the Worker key
        #     and the kubeconfig for authenticating with the Primaza cluster.
        secret_name = f"primaza-auth-{self.cluster_environment}"
        self.create_clustercontext_secret(secret_name, self.secret_cfg)

        # - In the created namespace, create a Service Account for the
        #   agent to be deployed in the namespace (named for example
        #   primaza-application-agent or primaza-service-agent)
        service_account_name = f"primaza-{self.type}-agent"
        service_account = ServiceAccount(self.kubeconfig.get_api_client(),
                                         service_account_name, self.namespace)
        service_account.create()

        # - In the created namespace, create the Role for the
        #   agent (named for example primaza-application-agent or
        #   primaza-service-agent), that will grant it access to
        #   namespace and its resources
        # - In the created namespace, create a RoleBinding for binding
        #   the agents' Service Account to the role defined above
        self.install_roles()

        # - In the created namespace, create a Role (named
        #   primaza-application or primaza-service), that will grant
        #   primaza access to namespace and its resources
        #   (e.g. create ServiceClaim, create RegisteredServices)
        #
        #    Reminder: the primaza user is created on worker cluster setup
        api_client = self.kubeconfig.get_api_client()
        primaza_policy = get_primaza_namespace_role(self.main_user)
        primaza_role = Role(api_client, self.main_user, primaza_policy)
        primaza_role.create()

        # - In the created namespace, RoleBinding for binding the user primaza
        #   to the role defined above
        primaza_binding = RoleBinding(api_client,
                                      f"{self.main_user}-"
                                      f"{self.type}-binding",
                                      self.namespace,
                                      self.main_user,
                                      service_account_name)
        primaza_binding. create()

    def install_roles(self):
        logger.log_entry(f"config: {self.role_config}")
        out, err = self.kubectl_do(f"apply -f {self.role_config}")
        if err == 0:
            logger.log_entry("Deploy namespace config completed")

        logger.log_info(out)
        if err != 0:
            raise RuntimeError(
                "error deploying namespace config into "
                f"cluster {self.cluster_name}")

    def check(self):

        if self.type == APPLICATION:
            # For applications namespaces, Service Account
            # primaza-application-agent must be able to perform
            # the following actions:
            # - read,list Secrets
            self.__check_secrets()
            # - read,list,watch ServiceBinding
            self.__check_servicebinding()
            # - read,list,update/watch Deployments
            self.__check_deployments(True)
            # - read,list,update Pods
            self.__check_pods()
        else:
            # For services namespaces, Service Account primaza-service-agent
            # must be able to perform the following actions:
            # - read,list Services
            self.__check_services()
            # - read,list Deployments
            self.__check_deployments(False)

    def __check_secrets(self):
        # - read,list Secrets
        logger.log_entry()
        api_client = self.kubeconfig.get_api_client()
        list_secret = Secret(api_client, None, self.type, None)
        for secret in list_secret.list().items:
            logger.log_info(f"Secret found: {secret.metadata.name}")
            named_secret = Secret(api_client,
                                  secret.metadata.name,
                                  self.type, None)
            if not named_secret.read():
                logger.log_error(f"Failed to read secret : "
                                 f"{secret.metadata.name}")

    def __check_servicebinding(self):
        # - read,list,watch ServiceBinding
        logger.log_entry()

    def __check_deployments(self, update_watch):
        # - read,list,update/watch Deployments
        logger.log_entry(f"Include update/watch: {update_watch}")

    def __check_pods(self):
        # - read,list,update Pods
        logger.log_entry()

    def __check_services(self):
        # - read,list Services
        logger.log_entry()
