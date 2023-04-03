from kubernetes import client
from kubernetes.client.rest import ApiException
from primazactl.utils import logger


class Role(object):

    user: str = None
    role: client.V1ClusterRole = None
    rbac: client.RbacAuthorizationV1Api = None

    def __init__(self, api_client: client,
                 user: str,
                 role: client.V1ClusterRole):
        self.rbac = client.RbacAuthorizationV1Api(api_client)
        self.user = user
        self.role = role

    def create(self):
        logger.log_entry(f"User: {self.user}")

        if not self.read():
            try:
                self.rbac.create_cluster_role(self.role)
            except ApiException as e:
                logger.log_error("Exception when calling "
                                 "create_cluster_role: %s\n" % e)
                raise e

    def read(self) -> client.V1ClusterRole | None:
        logger.log_entry(f"User: {self.user}")

        try:
            return self.rbac.read_cluster_role(self.user)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "read_cluster_role: %s\n" % e)
                raise e
        return None

    def delete(self):
        logger.log_entry(f"User: {self.user}")

        try:
            return self.rbac.delete_cluster_role(self.user)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "delete_cluster_role: %s\n" % e)
                raise e
