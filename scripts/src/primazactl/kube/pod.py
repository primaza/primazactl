import time
from kubernetes import client
from kubernetes.client.rest import ApiException
from primazactl.utils import logger


class Pod(object):

    namespace: str = None
    corev1: client.CoreV1Api = None
    name: str = None

    def __init__(self, api_client, namespace):

        self.namespace = namespace
        self.corev1 = client.CoreV1Api(api_client)

    def get_primaza_pod_name(self):
        logger.log_entry(f"namespace: {self.namespace}")

        try:
            pods_resp = self.corev1.list_namespaced_pod(self.namespace)
            for pod in pods_resp.items:
                if pod.metadata.name.startswith("primaza-controller"):
                    logger.log_info(f"Pod found: {pod.metadata.name}")
                    self.name = pod.metadata.name
                    break
            return self.name
        except ApiException as e:
            logger.log_error('FAILED: list pods for namespace '
                             f'{self.namespace} '
                             "Exception: %s\n" % e)
            raise e

    def wait_for_running(self):

        logger.log_entry(f"namespace: {self.namespace}, name: {self.name}")

        error_msg = None
        pod_running = False
        if self.name:
            for i in range(1, 30):
                try:
                    status = self.corev1.read_namespaced_pod_status(
                        self.name,
                        self.namespace)
                    container_status = status.status.container_statuses[0]
                    if container_status.state.running:
                        logger.log_info(f"pod is running: "
                                        f"{container_status.state.running}")
                        pod_running = True
                        break
                    elif container_status.state.waiting.message:
                        error_msg = container_status.state.waiting.message
                        logger.log_error(f"pod failed: {error_msg}")
                        break
                    else:
                        logger.log_info(f"{i} of 30. Pod is not running "
                                        f"yet, sleep and try again")
                        time.sleep(2)
                except ApiException as e:
                    if e.reason == "Not Found":
                        logger.log_info(f"{i} of 30. Pod not found, "
                                        "sleep and try again", True)
                        time.sleep(2)
                    else:
                        logger.log_error("Exception when reading "
                                         "pod information: %s\n" % e)
                        raise e

        if not pod_running and not error_msg:
            error_msg = "Timed out waiting for pod to start"
            logger.log_error(error_msg)

        return error_msg
