from kubeconfig import KubeConfig
import yaml
from kubernetes import client, config
from primazactl.utils import logger


class KubeConfigWrapper(object):

    kube_config_file: str = None
    kube_config_content = None
    cluster_name: str = None

    def __init__(self, cluster_name: str | None, kube_config_file: str):
        self.kube_config_file = kube_config_file
        if not cluster_name:
            self.cluster_name = self.get_context()
            logger.log_info(f"kcw: Use context cluster: {self.cluster_name}")
        else:
            self.cluster_name = cluster_name
        logger.log_info(f"kcw: cluster: {self.cluster_name}, "
                        f"file: {self.kube_config_file}")

    def use_context(self):
        logger.log_entry(f"Cluster: {self.cluster_name}, "
                         f"File : {self.kube_config_file}")
        if self.kube_config_file:
            config = KubeConfig(self.kube_config_file)
            config.use_context(f"{self.cluster_name}")
        else:
            config = self.get_kube_config_content_as_yaml()
            config["current-context"] = self.cluster_name

    def get_context(self):
        if self.kube_config_file:
            config = KubeConfig(self.kube_config_file)
            return config.current_context()
        else:
            config = self.get_kube_config_content_as_yaml()
            return config["current-context"]

    def get_kube_config_content_as_yaml(self):
        if not self.kube_config_content:
            self.get_kube_config_content()
        return yaml.safe_load(self.kube_config_content)

    def get_kube_config_content(self):
        if not self.kube_config_content:
            with open(str(self.kube_config_file), "r") as kc_file:
                self.kube_config_content = kc_file.read()
        return self.kube_config_content

    def get_kubeconfig_for_content(self, content):
        kcw = KubeConfigWrapper(self.cluster_name, None)
        kcw.kube_config_content = content
        return kcw

    def get_kube_config_for_cluster(self):
        logger.log_entry(f"Cluster: {self.cluster_name}, "
                         f"File : {self.kube_config_file}")

        kcc_yaml = self.get_kube_config_content_as_yaml()

        cluster_config = {"apiVersion": "v1",
                          "kind": kcc_yaml["kind"],
                          "preferences": kcc_yaml["preferences"],
                          "current-context": self.cluster_name}

        logger.log_info("look through clusters")
        for cluster in kcc_yaml["clusters"]:
            if cluster["name"] == self.cluster_name:
                logger.log_info(f"cluster found: {self.cluster_name}")
                cluster_config["clusters"] = [cluster]
                break

        logger.log_info("look through users")
        for user in kcc_yaml["users"]:
            if user["name"] == self.cluster_name:
                logger.log_info(f"user found: {self.cluster_name}")
                cluster_config["users"] = [user]
                break

        logger.log_info("look through contexts")
        for context in kcc_yaml["contexts"]:
            if context["name"] == self.cluster_name:
                cluster_config["contexts"] = [context]
                logger.log_info(f"context found: {self.cluster_name}")
                break

        kcw = KubeConfigWrapper(self.cluster_name, None)
        kcw.kube_config_content = yaml.dump(cluster_config)
        # logger.log_info(f"Kubeconfig:\n{kcw.kube_config_content}")
        return kcw

    def copy_to_temp_file(self, temp_file):
        logger.log_entry(f"Cluster: {self.cluster_name}, "
                         f"File : {temp_file}")
        temp_file.write(self.get_kube_config_content().encode("utf-8"))
        return KubeConfigWrapper(self.cluster_name, temp_file.name)

    def get_kube_config_file(self):
        return self.kube_config_file

    def get_cluster_name(self):
        return self.cluster_name

    def get_api_client(self) -> client:
        try:
            if self.kube_config_file:
                self.use_context()
                config.load_kube_config(config_file=self.kube_config_file)
                return client.ApiClient()
            else:
                content = yaml.safe_load(self.get_kube_config_content())
                cluster_only_api_client = \
                    config.new_client_from_config_dict(content)
                return cluster_only_api_client
        except Exception as e:
            msg = f"Exception getting kubernetes client for cluster " \
                  f"{self.cluster_name} in {self.kube_config_file}. " \
                  f"Exception was {e}"
            logger.log_error(msg)
            raise RuntimeError(f"[ERROR] {msg}")
