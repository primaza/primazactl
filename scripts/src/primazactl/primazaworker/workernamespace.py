from primazactl.utils import logger
from primazactl.primazamain.primazamain import PrimazaMain
from .primazaworker import PrimazaWorker
from primazactl.kube.namespace import Namespace
from primazactl.kube.serviceaccount import ServiceAccount
from primazactl.kube.role import Role
from primazactl.kube.rolebinding import RoleBinding
from primazactl.kube.roles.primazaroles import \
    get_application_agent_role, \
    get_service_agent_role, \
    get_primaza_namespace_role
from primazactl.cmd.worker.create.constants import APPLICATIONS
from primazactl.primaza.primaza import Primaza


class WorkerNamespace(Primaza):

    main_cluster: str = None
    type: str = None
    kube_namesapce: Namespace = None
    cluster_environment: str = None

    def __init__(self, type,
                 cluster_environment,
                 worker_cluster,
                 main_cluster):

        super().__init__(type,
                         worker_cluster,
                         f"primaza-{self.type}-agent",
                         None)

        self.type = type
        self.main_cluster = main_cluster
        api_client = self.kubeconfig.get_api_client()
        self.namespace = self.type
        self.cluster_environment = cluster_environment
        self.kube_namespace = Namespace(api_client, self.type)

    def create(self):
        logger.log_entry(f"namespace type: {self.type}, "
                         f"cluster environment: {self.cluster_environment}, "
                         f"worker cluster: {self.cluster_name}, "
                         f"main_cluster: {self.main_cluster}")

        self.primaza_main = PrimazaMain(
            cluster_name=self.main_cluster,
            kubeconfig_path=None,
            config_file=None,
            version=None,
        )

        worker = PrimazaWorker(
            primaza_main=None,
            cluster_name=self.cluster_name,
            kubeconfig_file=None,
            config_file=None,
            version=None,
            environment=None,
            cluster_environment=self.cluster_environment,
        )

        # On primaza main
        # - Use the Worker key to create a CertificateSigningRequest (CSR)
        #   named after the Cluster Environment and the Environment, like
        #   primaza-$CLUSTER_ENVIRONMENT_NAME
        # - Approve the CSR
        # - Create a kubeconfig with CSR's Certificate
        self.primaza_main.\
            create_primaza_service_account(self.cluster_environment)
        secret_name = f"primaza-{self.cluster_environment}"
        cc_kubeconfig = self.primaza_main.get_kubeconfig(
            self.primaza_main.user,
            self.cluster_name)
        worker.create_clustercontext_secret(secret_name, cc_kubeconfig)

        # On worker cluster
        # - create the namespace
        self.kube_namespace.create()

        # - in the created namespace, create the Secret
        #     'primaza-auth-$CLUSTER_ENVIRONMENT' the Worker key
        #     and the kubeconfig for authenticating with the Primaza cluster.
        secret_name = f"primaza-auth-{self.cluster_environment}"
        self.create_clustercontext_secret(secret_name, cc_kubeconfig)

        # - In the created namespace, create a Service Account for the
        #   agent to be deployed in the namespace (named for example
        #   primaza-application-agent or primaza-service-agent)
        user = f"primaza-{self.type}-agent"
        service_account = ServiceAccount(self.kubeconfig.get_api_client(),
                                         user, self.namespace)
        service_account.create()

        # - In the created namespace, create the Role for the
        #   agent (named for example primaza-application-agent or
        #   primaza-service-agent), that will grant it access to
        #   namespace and its resources
        agent_policy = get_application_agent_role(user) \
            if self.type == APPLICATIONS \
            else get_service_agent_role(user)
        api_client = self.kubeconfig.get_api_client()
        agent_role = Role(api_client, user, agent_policy)
        agent_role.create()

        # - In the created namespace, create a RoleBinding for binding
        #   the agents' Service Account to the role defined above
        agent_binding = RoleBinding(api_client,
                                    f"{user}-binding",
                                    agent_role.user)
        agent_binding. create()

        # - In the created namespace, create a Role (named
        #   primaza-application or primaza-service), that will grant
        #   primaza access to namespace and its resources
        #   (e.g. create ServiceClaim, create RegisteredServices)
        #
        #    Reminder: the primaza user is created on worker cluster setup
        primaza_policy = get_primaza_namespace_role(self.primaza_main.user)
        primaza_role = Role(api_client, user, primaza_policy)
        primaza_role.create()

        # - In the created namespace, RoleBinding for binding the user primaza
        #   to the role defined above
        primaza_binding = RoleBinding(api_client,
                                      f"{self.primaza_main.user}-"
                                      f"{self.type}-binding",
                                      primaza_role.user)
        primaza_binding. create()
