from kubernetes import client
from kubernetes.client.rest import ApiException
from primazactl.utils import logger


class RoleBinding(object):

    user: str = None
    name: str = None
    rbac: client.RbacAuthorizationV1Api = None

    def __init__(self, api_client: client, binding_name: str, user: str):

        self.rbac = client.RbacAuthorizationV1Api(api_client)
        self.name = binding_name
        self.user = user

    def create(self):
        logger.log_entry(f"Name: {self.name}, user {self.user}")

        if not self.read():
            binding = client.V1ClusterRoleBinding(
                metadata=client.V1ObjectMeta(name=self.name),
                role_ref=client.V1RoleRef(
                    api_group="rbac.authorization.k8s.io",
                    kind="ClusterRole",
                    name=self.user),
                subjects=[
                    client.V1Subject(api_group="rbac.authorization.k8s.io",
                                     kind="User", name=self.user),
                ])
            try:
                self.rbac.create_cluster_role_binding(binding)
            except ApiException as e:
                logger.log_error("Exception when calling "
                                 "create_cluster_role_binding: %s\n" % e)
                raise e

    def read(self) -> str:
        logger.log_entry(f"Name: {self.name}, user {self.user}")

        try:
            return self.rbac.read_cluster_role_binding(name=self.name)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "read_cluster_role_binding: %s\n" % e)
                raise e
        return ""

    def delete(self) -> str:
        logger.log_entry(f"Name: {self.name}, user {self.user}")

        try:
            self.rbac.delete_cluster_role_binding(name=self.user)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "read_cluster_role_binding: %s\n" % e)
                raise e
