from kubernetes import client
from kubernetes.client.rest import ApiException
from primazactl.utils import logger


class Role(object):

    name: str = None
    role: client.V1Role = None
    rbac: client.RbacAuthorizationV1Api = None
    namespace: str = None

    def __init__(self, api_client: client,
                 name: str,
                 namespace: str,
                 role: client.V1Role):
        self.rbac = client.RbacAuthorizationV1Api(api_client)
        self.name = name
        self.role = role
        self.namespace = namespace

    def create(self):
        logger.log_entry(f"User: {self.name}")

        if not self.read():
            try:
                self.rbac.create_namespaced_role(self.namespace,
                                                 self.role)
            except ApiException as e:
                logger.log_error("Exception when calling "
                                 "create_cluster_role: %s\n" % e)
                raise e
        else:
            logger.log_info(self.read())

    def read(self) -> client.V1ClusterRole | None:
        logger.log_entry(f"User: {self.name}")

        try:
            return self.rbac.read_namespaced_role(self.name, self.namespace)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "read_cluster_role: %s\n" % e)
                raise e
        return None

    def delete(self):
        logger.log_entry(f"User: {self.name}")

        try:
            return self.rbac.delete_namesapced_role(self.name, self.namespace)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "delete_cluster_role: %s\n" % e)
                raise e

    def get_rules(self):
        logger.log_entry(f"User: {self.name}")
        policy = self.read()
        if policy:
            return policy.rules
        return None
