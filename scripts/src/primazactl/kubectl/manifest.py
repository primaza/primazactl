
import yaml
from kubernetes import client
from primazactl.utils import logger
from github import Github
import semver
import requests
from.constants import REPOSITORY
from.apply import apply_manifest


class Manifest(object):

    path: str = None
    version: str = None
    type: str = None
    namespace: str = None

    def __init__(self, namespace: str, path: str,
                 version: str = None, type: str = None):
        self.path = path
        self.namespace = namespace
        self.version = version
        self.type = type

    def update_namespace(self, body):
        logger.log_entry(f"namesapce: {self.namespace}")
        for resource in body:
            logger.log_info(f'resource: {resource["kind"]}')
            if resource["kind"] == "Namespace":
                update_dict(resource, "name", self.namespace)
            else:
                update_dict(resource, "namespace", self.namespace)

    def load_manifest(self):
        logger.log_entry(f"path: {self.path}, version: {self.version}, "
                         f"type: {self.type}")
        if self.path:
            with open(self.path, 'r') as manifest:
                self.body = yaml.safe_load_all(manifest)
                self.update_namespace()
        else:
            manifest = self.__set_config_content()
            self.body = yaml.safe_load_all(manifest)
            self.update_namespace()

    def apply(self, api_client: client, action: str = "create"):
        logger.log_entry(f"action: {action}")

        if self.path:
            with open(self.path, 'r') as manifest:
                self.__apply(manifest, api_client, action)
        else:
            self.__apply(self.__set_config_content(), api_client, action)

    def __apply(self, manifest, api_client, action):

        body = yaml.safe_load_all(manifest)
        body_list = list(body)
        self.update_namespace(body_list)

        errors = apply_manifest(body_list, api_client, action)
        if len(errors) > 0:
            msg = f"error performing {action} with config " \
                  f"{self.type} into namespace {self.namesapace} " \
                  f"{errors}"

            logger.log_error(msg)
            raise RuntimeError(msg)

    def __set_config_content(self):
        logger.log_entry()
        g = Github()
        repo = g.get_repo(REPOSITORY)

        releases = repo.get_releases()
        latest_release = None

        for release in releases:
            logger.log_info(f"release found - name: {release.id}")
            logger.log_info(f"                tag: {release.tag_name}")

            if self.version == "latest":
                if release.tag_name == "latest":
                    return self.__get_config_content(release)

            elif semver.VersionInfo.isvalid(release.tag_name):
                if self.version and \
                        semver.compare(self.version, release.tag_name) == 0:
                    logger.log_info(f"match found: {release.tag_name}")
                    return self.__get_config_content(release)
                elif not latest_release or \
                        semver.compare(release.tag_name,
                                       latest_release.tag_name) > 1:
                    logger.log_info(f"later match found: {release.tag_name}")
                    latest_release = release

        if latest_release:
            return self.__get_config_content(latest_release)

        raise RuntimeError(f"A release was not found in repository "
                           f"{REPOSITORY} for version {self.version}")

    def __get_config_content(self, release):
        logger.log_entry(f"release = {release.tag_name}")
        asset_name = f"{self.type}_{release.tag_name}.yaml"
        logger.log_info(f"Look for file : {asset_name}")
        for asset in release.get_assets():
            logger.log_info(f"asset found : {asset.name}")

            if asset.name == asset_name:
                logger.log_info("found required asset!")
                response = requests.get(asset.browser_download_url)
                return response.text.encode("utf-8")

        raise RuntimeError(f"Failed to get release asset {asset_name} "
                           f"from {REPOSITORY} "
                           f"for version {self.version}")


def update_list(items: [], key: str, new_value: str):
    for item in items:
        if not isinstance(item, str):
            if isinstance(item, dict):
                update_dict(item, key, new_value)
            elif isinstance(item, list):
                update_list(item, key, new_value)


def update_dict(body: {}, key: str, new_value: str):
    for entry in body:
        if isinstance(body[entry], dict):
            update_dict(body[entry], key, new_value)
        elif isinstance(body[entry], list):
            update_list(body[entry], key, new_value)
        elif entry == key:
            body[entry] = new_value
