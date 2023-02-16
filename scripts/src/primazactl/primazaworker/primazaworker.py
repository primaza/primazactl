
from urllib.parse import urlparse
from primazactl.kubeconfigcontent import KubeConfigContent


class PrimazaWorker(object):

    worker_namespace: str = None
    kube_config_file: str = None
    worker_cluster_name: str = None

    def __init__(self, cluster_name: str,
                 kubeconfigfile: str,
                 namespace: str = "primaza-system-worker"):
        print("Init called")
        self.worker_cluster_name = cluster_name
        self.kube_config_file = kubeconfigfile
        self.worker_namespace = namespace

    def update_kube_config(self, kubeconfigfile: str):
        kube_config = KubeConfigContent(self.primaza_cluster_name,
                                        kubeconfigfile)
        server_url = kube_config.get_server_url()
        url = urlparse(server_url)
        new_url = url._replace(netloc=url.hostname+':6443').geturl()
        kube_config.set_server_url(new_url)
        print(f'new_url {new_url}')
