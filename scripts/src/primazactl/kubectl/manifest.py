import os
import yaml
from kubernetes import client
from primazactl.utils import logger, settings
from github import Auth, Github
import semver
import requests
from.constants import get_repository
from.apply import apply_manifest


class Manifest(object):

    path: str = None
    version: str = None
    type: str = None
    namespace: str = None

    def __init__(self, namespace: str, path: str,
                 version: str = None, type: str = None):
        logger.log_entry(f"namespace: {namespace}, path: {path}, "
                         f"version: {version}, type: {type}")
        self.path = path
        self.namespace = namespace
        if version:
            self.version = version[1:] if version.startswith("v") else version
        self.type = type

    def replace_ns(self, body):
        d = yaml.dump({"body": body})  # type: str
        r = d.replace("primaza-system", self.namespace)
        return yaml.safe_load(r)["body"]

    def update_namespace(self, body):
        logger.log_entry(f"namespace: {self.namespace}")
        for resource in body:
            logger.log_info(f'resource: {resource["kind"]}')
            if resource["kind"] == "Certificate":
                names = resource["spec"]["dnsNames"]
                new_names = []
                for name in names:
                    nn = name.split(".")
                    nn[1] = self.namespace
                    new_names.append(".".join(nn))
                resource["spec"]["dnsNames"] = new_names
                update_dict(resource, "namespace", self.namespace)
            elif resource["kind"] == "ValidatingWebhookConfiguration":
                # FIXME: find a smarter way
                nr = self.replace_ns(resource)
                resource["metadata"] = nr["metadata"]
                resource["webhooks"] = nr["webhooks"]
            elif resource["kind"] == "Namespace":
                update_dict(resource, "name", self.namespace)
            else:
                update_dict(resource, "namespace", self.namespace)

    def load_manifest(self):
        logger.log_entry(f"path: {self.path}, version: {self.version}, "
                         f"type: {self.type}")
        if self.path:
            return yaml.safe_load_all(open(self.path, 'r'))
        else:
            manifest = self.__set_config_content()
            return yaml.safe_load_all(manifest)

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
                  f"{self.type} into namespace {self.namespace}"
            for error in errors:
                msg += f"\n{error}"

            logger.log_error(msg, not settings.dry_run_active())
            if not settings.dry_run_active():
                raise RuntimeError(msg)

    def build_github_client(self) -> Github:
        token = os.getenv("GITHUB_TOKEN", None)
        if not token:
            return Github()

        auth = Auth.Token(token)
        return Github(auth=auth)

    def __set_config_content(self):
        logger.log_entry()

        g = self.build_github_client()
        repo = g.get_repo(get_repository())

        releases = repo.get_releases()
        latest_release = None
        latest_version = None

        for release in releases:
            logger.log_info(f"release found - name: {release.id}")
            logger.log_info(f"                tag: {release.tag_name}")

            if self.version == "latest" and release.tag_name == "latest":
                return self.__get_config_content(release)
            elif self.version == "nightly" and release.tag_name == "nightly":
                return self.__get_config_content(release)
            elif self.version != "latest" and self.version != "nightly":
                version = release.tag_name[1:] \
                    if release.tag_name.startswith("v") \
                    else release.tag_name
                if semver.VersionInfo.isvalid(version):
                    if self.version and \
                            semver.compare(self.version, version) == 0:
                        logger.log_info(f"match found: {release.tag_name}")
                        return self.__get_config_content(release)
                    elif not latest_version or \
                            semver.compare(version,
                                           latest_version) > 1:
                        logger.log_info(f"later match found: "
                                        f"{release.tag_name}")
                        latest_version = version
                        latest_release = release
                else:
                    logger.log_info(f"Ignore release tag {release.tag_name} "
                                    f"- it is not a valid semver")

        if latest_release:
            return self.__get_config_content(latest_release)

        raise RuntimeError(f"A release was not found in repository "
                           f"{get_repository()} for version {self.version}")

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
                           f"from {get_repository()} "
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
