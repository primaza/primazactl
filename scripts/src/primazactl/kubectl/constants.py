import os

PRIMAZA_CONFIG: str = "control_plane_config"
WORKER_CONFIG: str = "crds_config"
APP_AGENT_CONFIG: str = "application_namespace_config"
SVC_AGENT_CONFIG: str = "service_namespace_config"
REPOSITORY: str = "primaza/primaza"
TEST_REPOSITORY_OVERRIDE: str = "primaza-test-only-repository-override"


def get_repository():
    override_repo = os.getenv(TEST_REPOSITORY_OVERRIDE)
    if override_repo:
        return override_repo
    return REPOSITORY
