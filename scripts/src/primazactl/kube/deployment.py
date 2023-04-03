from kubernetes import client
from kubernetes.client.rest import ApiException
from primazactl.utils import logger


class Deployment(object):

    name: str = None
    appsv1: client.AppsV1Api = None
    namespace: str = None

    def __init__(self, api_client: client, name: str, namespace: str):
        self.name = name
        self.appsv1 = client.AppsV1Api(api_client)
        self.namespace = namespace

    def create(self):
        logger.log_entry(f"name: {self.name}, namespace: {self.namespace}")

        if not self.read():
            deployment = client.V1Deployment(
                metadata=client.V1ObjectMeta(name=self.name,
                                             namespace=self.namespace),
                spec=client.V1DeploymentSpec(
                    replicas=1,
                    selector=client.V1LabelSelector(),
                    template=client.V1PodTemplateSpec()))

            try:
                self.appsv1.create_namespaced_deployment(self.namespace,
                                                         deployment)
            except ApiException as e:
                logger.log_error("Exception when calling "
                                 "create_namespaced_deployment: %s\n" % e)
                raise e

    def read(self) -> str:
        logger.log_entry(f"name: {self.name}, namespace: {self.namespace}")

        try:
            return self.appsv1.read_namespaced_deployment(self.name,
                                                          self.namespace)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "read_namespaced_deployment: %s\n" % e)
                raise e
        return ""

    def update(self):
        logger.log_entry(f"name: {self.name}, namespace: {self.namespace}")

        try:
            deployment = client.V1Deployment(
                metadata=client.V1ObjectMeta(name=self.name,
                                             namespace=self.namespace),
                spec=client.V1DeploymentSpec(replicas=2))

            self.appsv1.patch_namespaced_deployment(self.name,
                                                    self.namespace,
                                                    deployment)
        except ApiException as e:
            logger.log_error("Exception when calling "
                             "patch_namespaced_deployment: %s\n" % e)
            raise e

    def delete(self):
        logger.log_entry(f"name: {self.name}, namespace: {self.namespace}")

        try:
            self.appsv1.delete_namespaced_deployment(self.name,
                                                     self.namespace)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "delete_namespaced_deployment: %s\n" % e)
                raise e
