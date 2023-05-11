from kubernetes import client
from kubernetes.client.rest import ApiException
from primazactl.utils import logger


class RoleBinding(object):

    user: str = None
    name: str = None
    rbac: client.RbacAuthorizationV1Api = None
    service_account: str = None
    service_account_namespace: str = None
    namespace: str = None

    def __init__(self, api_client: client, binding_name: str,
                 namespace: str, user: str,
                 service_account_namespace: str, service_account: str):

        self.rbac = client.RbacAuthorizationV1Api(api_client)
        self.name = binding_name
        self.user = user
        self.service_account = service_account
        self.service_account_namespace = service_account_namespace
        self.namespace = namespace

    def create(self):
        logger.log_entry(f"Name: {self.name}, user {self.user}, "
                         f"namespace : {self.namespace}, "
                         f"service account: {self.service_account}")

        if not self.read():
            binding = client.V1RoleBinding(
                kind="RoleBinding",
                metadata=client.V1ObjectMeta(
                    name=self.name,
                    namespace=self.namespace,
                    labels={"app.kubernetes.io/component": "coreV1",
                            "app.kubernetes.io/created-by": "primaza",
                            "app.kubernetes.io/instance":
                                self.name.replace(":", "-"),
                            "app.kubernetes.io/managed-by": "primazactl",
                            "app.kubernetes.io/name": "rolebinding",
                            "app.kubernetes.io/part-of": "primaza"}),
                role_ref=client.V1RoleRef(
                    api_group="rbac.authorization.k8s.io",
                    kind="Role",
                    name=self.user),
                subjects=[
                    client.V1Subject(namespace=self.service_account_namespace,
                                     kind="ServiceAccount",
                                     name=self.service_account),
                ])
            try:
                self.rbac.create_namespaced_role_binding(
                    namespace=self.namespace,
                    body=binding)
            except ApiException as e:
                logger.log_error("Exception when calling "
                                 "create_cluster_role_binding: %s\n" % e)
                raise e

    def read(self) -> client.V1RoleBinding | None:
        logger.log_entry(f"Name: {self.name}, user {self.user}")

        try:
            return self.rbac.read_namespaced_role_binding(
                name=self.name,
                namespace=self.namespace)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "read_cluster_role_binding: %s\n" % e)
                raise e
        return None

    def delete(self) -> str:
        logger.log_entry(f"Name: {self.name}, user {self.user}")

        try:
            self.rbac.delete_namespaced_role_binding(name=self.name,
                                                     namespace=self.namespace)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "read_cluster_role_binding: %s\n" % e)
                raise e
