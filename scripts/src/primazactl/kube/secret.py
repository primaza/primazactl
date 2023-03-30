from kubernetes import client
from kubernetes.client.rest import ApiException
from primazactl.utils import logger


class Secret(object):

    name: str = None
    namespace: str = None
    kubeconfig: str = None
    corev1: client.CoreV1Api = None

    def __init__(self, api_client: client, name: str,
                 namespace: str, kubeconfig: str):
        self.name = name
        self.namespace = namespace
        self.kubeconfig = kubeconfig
        self.corev1 = client.CoreV1Api(api_client)

    def create(self, secret: client.V1Secret = None):
        logger.log_entry(f"Secret name: {self.name}, "
                         f"namespace: {self.namespace}")

        if not self.read():
            if not secret:
                secret = client.V1Secret(
                    metadata=client.V1ObjectMeta(name=self.name),
                    string_data={"kubeconfig": self.kubeconfig})

            try:
                self.corev1.create_namespaced_secret(namespace=self.namespace,
                                                     body=secret)
            except ApiException as e:
                logger.log_error("Exception when calling "
                                 "create_namespaced_secret: %s\n" % e)
                raise e

    def read(self) -> str:
        logger.log_entry(f"Secret name: {self.name}, "
                         f"namespace: {self.namespace}")

        try:
            return self.corev1.read_namespaced_secret(
                name=self.name,
                namespace=self.namespace)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "read_namespaced_secret: %s\n" % e)
                raise e

        return ""

    def delete(self):
        logger.log_entry(f"Secret name: {self.name}, "
                         f"namespace: {self.namespace}")

        try:
            self.corev1.delete_namespaced_secret(name=self.name,
                                                 namespace=self.namespace)
        except ApiException as e:
            if e.reason != "Not Found":
                logger.log_error("Exception when calling "
                                 "delete_namespaced_secret: %s\n" % e)
                raise e
