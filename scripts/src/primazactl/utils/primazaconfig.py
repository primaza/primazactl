from github import Github
import semver
import requests
import tempfile
from primazactl.utils import command
from primazactl.utils import kubeconfigwrapper
from primazactl.utils import logger


class PrimazaConfig(object):

    version: str = None
    repository = "primaza/primazactl"
    config_file: str = None
    config_content: str = None
    type: str = None

    def __init__(self, type="main", config_file=None, version=None):
        self.version = version
        self.config_file = config_file
        self.type = type
        logger.log_info(f"Created - type:{type}, "
                        f"file:{config_file}, "
                        f"version:{version}")

    def set_content(self, content):
        self.config_content = content

    def __set_config_content(self):

        logger.log_entry()

        g = Github()
        repo = g.get_repo(self.repository)

        releases = repo.get_releases()
        latest_release = None

        for release in releases:
            logger.log_info(f"release found - name: {release.id}")
            logger.log_info(f"                tag: {release.tag_name}")

            if semver.VersionInfo.isvalid(release.tag_name):
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
                           f"{self.repository} for version {self.version}")

    def __get_config_content(self, release):

        logger.log_entry(f"release = {release}")
        asset_name = f"primaza_{self.type}_config_{release.tag_name}.yaml"
        for asset in release.get_assets():
            logger.log_info("asset found : {asset.name}")

            if asset.name == asset_name:
                logger.log_info("found required asset:")
                config = requests.get(asset.browser_download_url)
                self.config_content = config.encode("utf-8")

        raise RuntimeError(f"A {asset_name} file was not found for "
                           f"version {self.version}")

    def apply(self, kcw: kubeconfigwrapper.KubeConfigWrapper):

        logger.log_entry()
        temp_file = tempfile.NamedTemporaryFile(
            prefix=f"kubeconfig-primaza-{kcw.get_cluster_name()}-")

        kcw = kcw.copy_to_temp_file(temp_file)

        # make sure we deploy to the required cluster
        kcw.use_context()

        logger.log_info(f"kubeconfig \n {kcw.get_kube_config_content}")

        if self.config_file:
            out, err = command.Command(). \
                setenv("KUBECONFIG", kcw.get_kube_config_file()). \
                run(f"kubectl apply -f {self.config_file}")
        else:
            if not self.config_content:
                self.__set_config_content()
            out, err = command.Command(). \
                setenv("KUBECONFIG", kcw.get_kube_config_file()). \
                run("kubectl apply -f -", self.config_content)

        logger.log_exit(out)
        return err
