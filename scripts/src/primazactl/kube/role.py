from kubernetes import client
from kubernetes.client.rest import ApiException
from primazactl.utils import logger
from primazactl.utils import settings
import yaml


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
        settings.add_resource(self.role.to_dict())
        if not self.read():
            try:
                if settings.dry_run:
                    self.rbac.create_namespaced_role(self.namespace,
                                                     self.role,
                                                     dry_run="All")
                else:
                    self.rbac.create_namespaced_role(self.namespace,
                                                     self.role)
                logger.log_info('SUCCESS: create of Role '
                                f'{self.role.metadata.name}',
                                settings.dry_run)
            except ApiException as e:
                body = yaml.safe_load(e.body)
                logger.log_error('FAILED: create of Role '
                                 f'{self.role.metadata.name} '
                                 f'Exception: {body["message"]}')
                if not settings.dry_run:
                    raise e
        else:
            logger.log_info('UNCHANGED: Role '
                            f'{self.role.metadata.name} already exists',
                            settings.dry_run)

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
