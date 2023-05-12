from primazactl.utils import logger
from primazactl.cmd.create.namespace.constants import APPLICATION
from primazactl.kube.customnamespaced import CustomNamespaced


def create_body(name, namespace, environment, secret_name):
    if name and environment and secret_name:
        return {
            "apiVersion": "primaza.io/v1alpha1",
            "kind": "ClusterEnvironment",
            "metadata": {
                "name": name,
                "namespace": namespace,
            },
            "spec": {
                "environmentName": environment,
                "clusterContextSecret": secret_name,
            }
        }
    else:
        return None


class ClusterEnvironment(CustomNamespaced):

    name: str = None
    namespace: str = None
    custom_namespaced: CustomNamespaced = None
    body: {} = None

    def __init__(self, api_client,
                 namespace, name=None,
                 environment=None, secret_name=None):

        super().__init__(api_client,
                         "primaza.io",
                         "v1alpha1",
                         "ClusterEnvironment",
                         "clusterenvironments",
                         name,
                         namespace,
                         create_body(name, namespace,
                                     environment, secret_name))

    def add_namespace(self, type, name):
        logger.log_entry(f"type: {type}, name: {name}")
        if not self.body:
            self.read()

        if type == APPLICATION:
            entry = "applicationNamespaces"
        else:
            entry = "serviceNamespaces"

        if entry in self.body["spec"]:
            values = self.body["spec"][entry]
            values.append(name)
            self.body["spec"][entry] = values
        else:
            self.body["spec"][entry] = [name]

        logger.log_info(f'patch new spec: {self.body["spec"]}')

        self.patch(self.body)

    def check(self, state, ctype, cstatus):
        self.check_state(state)
        self.check_status_condition(ctype, cstatus)
        self.check_status_condition("ApplicationNamespacePermissionsRequired",
                                    "False")
        self.check_status_condition("ServiceNamespacePermissionsRequired",
                                    "False")
