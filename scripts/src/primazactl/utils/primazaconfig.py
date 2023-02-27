from github import Github
import semver
import requests


class PrimazaConfig(object):

    version: str = None
    repository = "primaza/primazactl"

    def __init__(self, version=None):
        self.version = version

    def get_config(self):

        g = Github()
        repo = g.get_repo(self.repository)

        releases = repo.get_releases()
        latest_release = None

        for release in releases:
            print(f"release found - name: {release.id}")
            print(f"                tag: {release.tag_name}")

            if semver.VersionInfo.isvalid(release.tag_name):
                if self.version and \
                        semver.compare(self.version, release.tag_name) == 0:
                    print(f"match found: {release.tag_name}")
                    return self.__get_config_file(release)
                elif not latest_release or \
                        semver.compare(release.tag_name,
                                       latest_release.tag_name) > 1:
                    print(f"later match found: {release.tag_name}")
                    latest_release = release

        if latest_release:
            return self.__get_config_file(latest_release)

        return ""

    def __get_config_file(self, release):

        for asset in release.get_assets():
            print("asset found : {asset.name}")
            if asset.name == f"primaza_config_{release.tag_name}.yaml":
                print("found required asset:")
                r = requests.get(asset.browser_download_url)
                return r.content.decode("utf8")

        raise RuntimeError("A primaza config file was not found for "
                           f"version {self.version}")
