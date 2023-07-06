from kubeconfig import KubeConfig
import yaml
from kubernetes import client, config
from primazactl.utils import logger


class KubeConfigWrapper(object):

    kube_config_file: str = None
    kube_config_content = None
    context: str = None
    user: str = None

    def __init__(self, context: str | None, kube_config_file: str):
        self.kube_config_file = kube_config_file
        if not context:
            self.context = self.get_context()
            logger.log_info(f"kcw: Use context cluster: {self.context}")
        else:
            self.context = context
        logger.log_info(f"kcw: cluster: {self.context}, "
                        f"file: {self.kube_config_file}")

    def use_context(self):
        logger.log_entry(f"Cluster: {self.context}, "
                         f"File : {self.kube_config_file}")
        if self.kube_config_file:
            config = KubeConfig(self.kube_config_file)
            config.use_context(f"{self.context}")
        else:
            config = self.get_kube_config_content_as_yaml()
            config["current-context"] = self.context

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
        kcw = KubeConfigWrapper(self.context, None)
        kcw.kube_config_content = content
        return kcw

    def get_kube_config_for_cluster(self):
        logger.log_entry(f"Cluster: {self.context}, "
                         f"File : {self.kube_config_file}")

        kcc_yaml = self.get_kube_config_content_as_yaml()

        cluster_config = {"apiVersion": "v1",
                          "kind": kcc_yaml["kind"],
                          "preferences": kcc_yaml["preferences"],
                          "current-context": self.context}

        context_cluster: str = None
        for context in kcc_yaml["contexts"]:
            if context["name"] == self.context:
                cluster_config["contexts"] = [context]
                logger.log_info(f"context found: {self.context}")
                self.user = context["context"]["user"]
                context_cluster = context["context"]["cluster"]
                break

        if self.user != self.context:
            for context in kcc_yaml["contexts"]:
                if context["name"] == self.user:
                    cluster_config["contexts"].append(context)
                    logger.log_info(f'context found: {context["name"]}')
                    break

        for cluster in kcc_yaml["clusters"]:
            if cluster["name"] == self.context or \
                    (context_cluster and cluster["name"] == context_cluster):
                logger.log_info(f'cluster found: {cluster["name"]}')
                cluster_config["clusters"] = [cluster]
                break

        if "clusters" not in cluster_config:
            context = self.context if not context_cluster \
                else context_cluster
            msg = f"Error cluster {context} not found in kube config: " \
                  f"{self.kube_config_file}"
            logger.log_error(msg)
            raise RuntimeError(f"[ERROR] {msg}")

        for user in kcc_yaml["users"]:
            if user["name"] == self.context or \
                    (self.user and user["name"] == self.user):
                logger.log_info(f'user found: {user["name"]}')
                if "users" in cluster_config:
                    cluster_config["users"].append(user)
                else:
                    cluster_config["users"] = [user]

        kcw = KubeConfigWrapper(self.context, self.kube_config_file)
        kcw.kube_config_content = yaml.dump(cluster_config)
        # logger.log_info(f"Kubeconfig:\n{yaml.dump(cluster_config)}")
        return kcw

    def copy_to_temp_file(self, temp_file):
        logger.log_entry(f"Cluster: {self.context}, "
                         f"File : {temp_file.name}")
        temp_file.write(str(self.kube_config_content))
        return KubeConfigWrapper(self.context, temp_file.name)

    def get_kube_config_file(self):
        return self.kube_config_file

    def get_api_client(self) -> client:

        logger.log_entry(self.context)
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
                  f"{self.context} in {self.kube_config_file}. " \
                  f"Exception was {e}"
            logger.log_error(msg)
            raise RuntimeError(f"[ERROR] {msg}")
