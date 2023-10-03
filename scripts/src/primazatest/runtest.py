import argparse
import subprocess
import sys
import time
import os
import yaml
import tempfile
from primazactl.utils.command import Command
from primazactl.kubectl.manifest import Manifest
from primazactl.kubectl.constants import PRIMAZA_CONFIG, WORKER_CONFIG, \
    APP_AGENT_CONFIG, SVC_AGENT_CONFIG, TEST_REPOSITORY_OVERRIDE

PASS = '\033[92mPASS\033[0m'
SUCCESS = '\033[92mSUCCESS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
FAILED = '\033[91mFAILED\033[0m'

TENANT = "primaza-controller-system"
CLUSTER_ENVIRONMENT = "primaza-environment"
SERVICE_NAMESPACE = "service-agent-system"
APPLICATION_NAMESPACE = "application-agent-system"
TENANT_FOR_OUTPUT = "primaza-system"
SERVICE_NAMESPACE_FOR_OUTPUT = "services"
APPLICATION_NAMESPACE_FOR_OUTPUT = "applications"
COMMAND_TENANT = "tenant"
COMMAND_JOIN = "join"
COMMAND_APP_NS = "application"
COMMAND_SVC_NS = "server"


def run_cmd(cmd, silent=False):

    if not silent:
        curr_time = time.strftime("%I:%M:%S %p", time.localtime())
        print(f"\n,---------,-\n| COMMAND: {curr_time} :"
              f" {' '.join(cmd)}\n'---------'-")

    ctl_out = subprocess.run(cmd, capture_output=True)

    out = ""
    if ctl_out.stdout:
        out = ctl_out.stdout.decode("utf-8")

    err = ""
    if ctl_out.stderr:
        err = ctl_out.stderr.decode("utf-8").strip()

    return out, err


def run_and_check(venv_dir, args, expect_msg, expect_error_msg, fail_msg):

    command = [f"{venv_dir}/bin/primazactl"]
    if args:
        command += args
    ctl_out, ctl_err = run_cmd(command)

    outcome = True

    print(f"command output:\n{ctl_out}")

    if expect_msg:
        if ctl_out:
            print(f"Response was:\n{ctl_out}")
            if expect_msg in ctl_out:
                print(f"\n+++[{PASS}] args: {args}\n")
            else:
                print(f"\n---[{FAIL}] args: {args} : {fail_msg}\n")
                outcome = False
        else:
            print(f"\n---[{FAIL}] args: {args} : {fail_msg}\n")
            outcome = False

    if expect_error_msg:
        if ctl_err:
            print(f"Error response was:\n{ctl_err}\n")
            if expect_error_msg in ctl_err:
                print(f"\n+++[{PASS}] args: {args}\n")
            else:
                print(f"Expected response to include:\n{expect_error_msg}\n")
                print(f"\n---[{FAIL}] args: {args} : {fail_msg}\n")
                outcome = False
        else:
            print(f"Response was:\n{ctl_out}\n")
            if ctl_out and expect_error_msg in ctl_out:
                print(f"\n+++[{PASS}] args: {args}\n")
            else:
                print(f"\n---[{FAIL}] args: {args} : {fail_msg}")
                outcome = False

    return outcome


def test_args(command_args):

    venv_dir = command_args.venv_dir

    outcome = True
    expect_msg = "usage: primazactl [-h]"
    fail_msg = "unexpected response to no arguments"
    outcome = outcome & run_and_check(venv_dir, None, expect_msg,
                                      None, fail_msg)

    args = ["create"]
    expect_msg = "usage: primazactl [-h]"
    fail_msg = "unexpected response to single argument"
    outcome = outcome & run_and_check(venv_dir, args, expect_msg,
                                      None, fail_msg)

    args = ["drink"]
    expect_error_msg = "error: argument {create,join,apply}: " \
        "invalid choice: 'drink' (choose from 'create', 'join', 'apply')"
    fail_msg = "unexpected response invalid action"
    outcome = outcome & run_and_check(venv_dir, args, None,
                                      expect_error_msg, fail_msg)

    args = ["create", "tenant", TENANT, "-k", "/.kube/DoesNotExist"]
    expect_error_msg = "error: argument -k/--kubeconfig: --config does not" \
                       " specify a valid file: /.kube/DoesNotExist"
    fail_msg = "unexpected response to bad kube config file"
    outcome = outcome & run_and_check(venv_dir, args, None,
                                      expect_error_msg, fail_msg)

    args = ["create", "tenant",
            TENANT, "-f", "scripts/config/DoesNotExist"]
    expect_error_msg = "error: argument -f/--config: --config does not " \
                       "specify a valid file: scripts/config/DoesNotExist"
    fail_msg = "unexpected response to bad config file"
    outcome = outcome & run_and_check(venv_dir, args, None,
                                      expect_error_msg, fail_msg)

    args = ["create", "tenant", TENANT, "-v", "version.not.semantic"]
    expect_error_msg = "error: argument -v/--version: --version is not a" \
                       " valid semantic version: version.not.semantic"
    fail_msg = "unexpected response to bad version"
    outcome = outcome & run_and_check(venv_dir, args, None,
                                      expect_error_msg, fail_msg)

    if command_args.version:
        args = ["create",
                "tenant",
                TENANT,
                "-c",
                "non-existent-cluster",
                "--version",
                command_args.version]
    else:
        args = ["create",
                "tenant",
                TENANT,
                "-c",
                "non-existent-cluster",
                "--config",
                command_args.main_config]

    expect_error_msg = "Error cluster non-existent-cluster not " \
                       "found in kube config"
    fail_msg = "unexpected response to bad cluster"
    outcome = outcome & run_and_check(venv_dir, args, None,
                                      expect_error_msg, fail_msg)

    return outcome


def test_main_install(venv_dir, config, version,
                      cluster, namespace, kubeconfig=None,
                      expect_out=False, dry_run=None, output=None):

    if version:
        command = [f"{venv_dir}/bin/primazactl",
                   "create",
                   "tenant",
                   namespace,
                   "-c", cluster,
                   "-v", version]
    else:
        command = [f"{venv_dir}/bin/primazactl",
                   "create",
                   "tenant",
                   namespace,
                   "-c", cluster,
                   "-f", config]

    if kubeconfig:
        command.append("-k")
        command.append(kubeconfig)
    if dry_run:
        command.append("-y")
        command.append(dry_run)
    if output:
        command.append("-o")
        command.append(output)

    out, err = run_cmd(command)

    if out and expect_out:
        return True, out

    if err:
        print(f"[{FAIL}] Unexpected error response: {err}")
        return False, None

    if f"Create primaza tenant {namespace} successfully completed" not in out:
        print(f"[{FAIL}] Unexpected response: {out}")
        return False, None

    print(f"[{PASS}] main installed.")
    return True, None


def get_cluster_internal_url(cluster_name: str) -> str:
    control_plane = f'{cluster_name}-control-plane'
    out, err = Command().run(f"docker inspect {control_plane}")
    if err != 0:
        raise RuntimeError("\n[ERROR] error getting data from docker:"
                           f"{control_plane} : {err}")
    docker_data = yaml.safe_load(out)
    networks = docker_data[0]["NetworkSettings"]["Networks"]
    ipaddr = networks["kind"]["IPAddress"]
    internal_url = f"https://{ipaddr}:6443"
    return internal_url


def test_worker_install(venv_dir, config, version, worker_cluster,
                        main_cluster, tenant, service_account_namespace=None,
                        kubeconfig=None,
                        main_kubeconfig=None, expect_out=False,
                        dry_run=None, output=None):

    internal_url = get_cluster_internal_url(
            worker_cluster.replace("kind-", ""))
    cluster_environment = CLUSTER_ENVIRONMENT

    if version:
        command = [f"{venv_dir}/bin/primazactl",
                   "join", "cluster",
                   "-e", "test",
                   "-d", cluster_environment,
                   "-c", worker_cluster,
                   "-m", main_cluster,
                   "-t", tenant,
                   "-v", version,
                   "-u", internal_url]
    else:
        command = [f"{venv_dir}/bin/primazactl",
                   "join", "cluster",
                   "-e", "test",
                   "-d", cluster_environment,
                   "-c", worker_cluster,
                   "-m", main_cluster,
                   "-t", tenant,
                   "-f", config,
                   "-u", internal_url]

    if kubeconfig:
        command.append("-k")
        command.append(kubeconfig)
    if main_kubeconfig:
        command.append("-l")
        command.append(main_kubeconfig)
    if dry_run:
        command.append("-y")
        command.append(dry_run)
    if output:
        command.append("-o")
        command.append(output)
    if service_account_namespace:
        command.append("-j")
        command.append(service_account_namespace)

    out, err = run_cmd(command)

    if out and expect_out:
        return True, out

    if err:
        print(f"[{FAIL}] Unexpected error response: {err}\n{out}")
        return False, None

    if f"Join cluster {cluster_environment} successfully completed" not in out:
        print(f"[{FAIL}] Unexpected response: {out}")
        return False, None

    print(f"[{PASS}] Join cluster {cluster_environment}\n\n{out}")
    return True, None


def test_application_namespace_create(venv_dir, namespace,
                                      worker_cluster,
                                      main_cluster, tenant,
                                      config, version,
                                      service_account_namespace=None,
                                      kubeconfig=None,
                                      main_kubeconfig=None,
                                      expect_out=False,
                                      dry_run=None,
                                      output=None):

    internal_url = get_cluster_internal_url(main_cluster.replace("kind-", ""))

    if version:
        command = [f"{venv_dir}/bin/primazactl",
                   "create", "application-namespace",
                   namespace,
                   "-d", CLUSTER_ENVIRONMENT,
                   "-c", worker_cluster,
                   "-m", main_cluster,
                   "-t", tenant,
                   "-v", version,
                   "-u", internal_url]
    else:
        command = [f"{venv_dir}/bin/primazactl",
                   "create", "application-namespace",
                   namespace,
                   "-d", CLUSTER_ENVIRONMENT,
                   "-c", worker_cluster,
                   "-m", main_cluster,
                   "-t", tenant,
                   "-f", config,
                   "-u", internal_url]

    if kubeconfig:
        command.append("-k")
        command.append(kubeconfig)
    if main_kubeconfig:
        command.append("-l")
        command.append(main_kubeconfig)
    if dry_run:
        command.append("-y")
        command.append(dry_run)
    if output:
        command.append("-o")
        command.append(output)
    if service_account_namespace:
        command.append("-j")
        command.append(service_account_namespace)

    out, err = run_cmd(command)
    if out and expect_out:
        return True, out

    if err:
        print(f"[{FAIL}] Unexpected error response: {err}")
        return False, None

    if f"Create application namespace {namespace} successfully completed" \
            not in out:
        print(f"[{FAIL}] Unexpected response: {out}")
        return False, None

    print(f"[{PASS}] Application namespace created\n\n{out}")
    return True, None


def test_service_namespace_create(venv_dir, namespace,
                                  worker_cluster,
                                  main_cluster, tenant,
                                  config,
                                  version,
                                  service_account_namespace=None,
                                  kubeconfig=None,
                                  main_kubeconfig=None,
                                  expect_out=False,
                                  dry_run=None,
                                  output=None):

    internal_url = get_cluster_internal_url(main_cluster.replace("kind-", ""))

    if version:
        command = [f"{venv_dir}/bin/primazactl",
                   "create", "service-namespace",
                   namespace,
                   "-d", CLUSTER_ENVIRONMENT,
                   "-c", worker_cluster,
                   "-m", main_cluster,
                   "-t", tenant,
                   "-v", version,
                   "-u", internal_url]
    else:
        command = [f"{venv_dir}/bin/primazactl",
                   "create", "service-namespace",
                   namespace,
                   "-d", CLUSTER_ENVIRONMENT,
                   "-c", worker_cluster,
                   "-m", main_cluster,
                   "-t", tenant,
                   "-f", config,
                   "-u", internal_url]

    if kubeconfig:
        command.append("-k")
        command.append(kubeconfig)
    if main_kubeconfig:
        command.append("-l")
        command.append(main_kubeconfig)
    if dry_run:
        command.append("-y")
        command.append(dry_run)
    if output:
        command.append("-o")
        command.append(output)
    if service_account_namespace:
        command.append("-j")
        command.append(service_account_namespace)

    out, err = run_cmd(command)

    if out and expect_out:
        return True, out

    if err:
        print(f"[{FAIL}] Unexpected error response: {err}")
        return False, None

    if f"Create service namespace {namespace} successfully completed" \
            not in out:
        print(f"[{FAIL}] Unexpected response: {out}")
        return False, None

    print(f"[{PASS}] Service namespace created\n\n{out}")
    return True, None


def test_with_user(command_args):

    configs_dir = command_args.input_dir
    if not configs_dir:
        configs_dir = "out/users"

    bad_kubeconfig = os.path.join(configs_dir, "tenant-bad-kube.config")
    expect_out = "User does not have permissions to create RegisteredService"
    bad_outcome, out = test_main_install(command_args.venv_dir,
                                         command_args.main_config,
                                         command_args.version,
                                         command_args.main_context,
                                         TENANT, bad_kubeconfig, True)

    print(f"response was:\n {out}")

    if expect_out in out:
        print(f"[{PASS}] Output includes expected text: {expect_out}")
    else:
        print(f"[{FAIL}] Unexpected response: {out}. "
              f"Expected to contain {expect_out}")
        bad_outcome = False

    main_kubeconfig = os.path.join(configs_dir, "tenant-kube.config")
    good_outcome, _ = test_main_install(command_args.venv_dir,
                                        command_args.main_config,
                                        command_args.version,
                                        command_args.main_context,
                                        TENANT, main_kubeconfig, False)

    outcome = bad_outcome & good_outcome

    bad_kubeconfig = os.path.join(configs_dir, "worker-bad-kube.config")
    expect_out = "User does not have permissions to create ServiceBinding"
    bad_outcome, out = test_worker_install(
        command_args.venv_dir,
        command_args.worker_config,
        command_args.version,
        command_args.worker_context,
        command_args.main_context,
        TENANT,
        command_args.service_account_namespace,
        bad_kubeconfig,
        main_kubeconfig, True)
    if expect_out in out:
        print(f"[{PASS}] Output includes expected text: {expect_out}")
    else:
        print(f"[{FAIL}] Unexpected response: {out}. "
              f"Expected to contain {expect_out}")
        bad_outcome = False

    worker_kubeconfig = os.path.join(configs_dir, "worker-kube.config")
    good_outcome, _ = test_worker_install(
        command_args.venv_dir,
        command_args.worker_config,
        command_args.version,
        command_args.worker_context,
        command_args.main_context,
        TENANT,
        command_args.service_account_namespace,
        worker_kubeconfig,
        main_kubeconfig, False)
    outcome = outcome & bad_outcome & good_outcome

    bad_kubeconfig = os.path.join(configs_dir,
                                  "application-agent-bad-kube.config")
    expect_out = "is attempting to grant RBAC permissions not currently held"
    bad_outcome, out = test_application_namespace_create(
        command_args.venv_dir,
        APPLICATION_NAMESPACE,
        command_args.worker_context,
        command_args.main_context,
        TENANT,
        command_args.app_config,
        command_args.version,
        command_args.service_account_namespace,
        bad_kubeconfig,
        main_kubeconfig,
        True)

    if expect_out in out:
        print(f"[{PASS}] Output includes expected text: {expect_out}")
    else:
        print(f"[{FAIL}] Unexpected response: {out}. "
              f"Expected to contain {expect_out}")
        bad_outcome = False

    app_kubeconfig = os.path.join(configs_dir,
                                  "application-agent-kube.config")
    good_outcome, _ = test_application_namespace_create(
        command_args.venv_dir,
        APPLICATION_NAMESPACE,
        command_args.worker_context,
        command_args.main_context,
        TENANT,
        command_args.app_config,
        command_args.version,
        command_args.service_account_namespace,
        app_kubeconfig,
        main_kubeconfig, False)
    outcome = outcome & bad_outcome & good_outcome

    bad_kubeconfig = os.path.join(configs_dir,
                                  "service-agent-bad-kube.config")
    expect_out = "is attempting to grant RBAC permissions not currently held"
    bad_outcome, out = test_service_namespace_create(
        command_args.venv_dir,
        SERVICE_NAMESPACE,
        command_args.worker_context,
        command_args.main_context,
        TENANT,
        command_args.app_config,
        command_args.version,
        command_args.service_account_namespace,
        bad_kubeconfig,
        main_kubeconfig,
        True)

    if expect_out in out:
        print(f"[{PASS}] Output includes expected text: {expect_out}")
    else:
        print(f"[{FAIL}] Unexpected response: {out}. "
              f"Expected to contain {expect_out}")
        bad_outcome = False

    svc_kubeconfig = os.path.join(configs_dir, "service-agent-kube.config")
    good_outcome, _ = test_service_namespace_create(
        command_args.venv_dir,
        SERVICE_NAMESPACE,
        command_args.worker_context,
        command_args.main_context,
        TENANT,
        command_args.app_config,
        command_args.version,
        command_args.service_account_namespace,
        svc_kubeconfig,
        main_kubeconfig,
        True)

    outcome = outcome & bad_outcome & good_outcome

    return outcome


def test_create(command_args):

    outcome, _ = test_main_install(command_args.venv_dir,
                                   command_args.main_config,
                                   command_args.version,
                                   command_args.main_context,
                                   TENANT)
    if(command_args.service_account_namespace and
       command_args.service_account_namespace != "kube-system"):
        run_cmd(["kubectl", "create", "namespace",
                command_args.service_account_namespace,
                "--context", command_args.worker_context])

    worker_outcome, _ = test_worker_install(
        command_args.venv_dir,
        command_args.worker_config,
        command_args.version,
        command_args.worker_context,
        command_args.main_context,
        TENANT,
        command_args.service_account_namespace)
    outcome = outcome & worker_outcome
    app_outcome, _ = test_application_namespace_create(
        command_args.venv_dir,
        APPLICATION_NAMESPACE,
        command_args.worker_context,
        command_args.main_context,
        TENANT,
        command_args.app_config,
        command_args.version,
        command_args.service_account_namespace,)
    outcome = outcome & app_outcome

    svc_outcome, _ = test_service_namespace_create(
        command_args.venv_dir,
        SERVICE_NAMESPACE,
        command_args.worker_context,
        command_args.main_context,
        TENANT,
        command_args.service_config,
        command_args.version,
        command_args.service_account_namespace,)

    return outcome & svc_outcome


def test_dry_run(command_args, dry_run_type):

    _, worker_resp = test_main_install(command_args.venv_dir,
                                       command_args.main_config,
                                       command_args.version,
                                       command_args.main_context,
                                       TENANT, None, True, dry_run_type, None)

    outcome = check_dry_run(dry_run_type,
                            command_args.main_config,
                            command_args.version,
                            worker_resp,
                            COMMAND_TENANT,
                            TENANT)
    if outcome:
        print(f"[{PASS}] {dry_run_type} dry run tenant {TENANT} "
              f"install test passed")
    else:
        print(f"[{FAIL}] {dry_run_type} dry run tenant {TENANT} "
              f"install test failed.")

    _, worker_resp = test_worker_install(
        command_args.venv_dir,
        command_args.worker_config,
        command_args.version,
        command_args.worker_context,
        command_args.main_context,
        TENANT,
        command_args.service_account_namespace,
        None, None,
        True, dry_run_type, None)

    worker_outcome = check_dry_run(dry_run_type,
                                   command_args.worker_config,
                                   command_args.version,
                                   worker_resp,
                                   COMMAND_JOIN,
                                   CLUSTER_ENVIRONMENT)
    if worker_outcome:
        print(f"[{PASS}] {dry_run_type} dry run worker join test passed")
    else:
        print(f"[{FAIL}] {dry_run_type} dry run worker join test failed")

    _, app_resp = test_application_namespace_create(
        command_args.venv_dir,
        APPLICATION_NAMESPACE,
        command_args.worker_context,
        command_args.main_context,
        TENANT,
        command_args.app_config,
        command_args.version,
        command_args.service_account_namespace,
        None, None, True, dry_run_type, None)

    app_outcome = check_dry_run(dry_run_type,
                                command_args.app_config,
                                command_args.version,
                                app_resp,
                                COMMAND_APP_NS,
                                APPLICATION_NAMESPACE)
    if app_outcome:
        print(f"[{PASS}] {dry_run_type} dry run application namespace "
              f"create test passed")
    else:
        print(f"[{FAIL}] {dry_run_type} dry run application namespace "
              f"create test failed")

    _, service_resp = test_service_namespace_create(
        command_args.venv_dir,
        SERVICE_NAMESPACE,
        command_args.worker_context,
        command_args.main_context,
        TENANT,
        command_args.service_config,
        command_args.version,
        command_args.service_account_namespace,
        None, None, True, dry_run_type, None)

    service_outcome = check_dry_run(dry_run_type,
                                    command_args.service_config,
                                    command_args.version,
                                    service_resp,
                                    COMMAND_SVC_NS,
                                    SERVICE_NAMESPACE)
    if service_outcome:
        print(f"[{PASS}] {dry_run_type} dry run service namespace "
              f"create test passed")
    else:
        print(f"[{FAIL}] {dry_run_type} dry run service namespace "
              f"create test failed")

    return outcome & worker_outcome & app_outcome & service_outcome


def test_dry_run_with_options(command_args):

    options_yaml = update_options_file(command_args)
    tenant = options_yaml["name"]
    cluster_options = options_yaml["clusterEnvironments"][0]
    cluster_env = cluster_options["name"]
    app_namespace = cluster_options["applicationNamespaces"][0]["name"]
    svc_namespace = cluster_options["serviceNamespaces"][0]["name"]

    with tempfile.NamedTemporaryFile(mode="w+") as options_file:
        with open(options_file.name, 'w') as options:
            yaml.dump(options_yaml, options)

        command = [f"{command_args.venv_dir}/bin/primazactl", "apply",
                   "-p", options_file.name,
                   "-y", "server"]
        resp, err = run_cmd(command)

        if err:
            print(f"[{FAIL}] Unexpected error response: {err}")
            outcome = False
        elif resp:
            outcome = True
            out_lines = None
            index = 0
            version = command_args.version
            for line in resp.splitlines():
                if line.strip(' \t\n\r') == "":
                    if index == 0:
                        cfg = command_args.main_config
                        cmd = COMMAND_TENANT
                        name = tenant
                        index = 1
                    elif index == 1:
                        cfg = command_args.worker_config
                        cmd = COMMAND_JOIN
                        name = cluster_env
                        index = 2
                    elif index == 2:
                        cfg = command_args.app_config
                        cmd = COMMAND_APP_NS
                        name = app_namespace
                        index = 3
                    elif index == 3:
                        cfg = command_args.service_config
                        cmd = COMMAND_SVC_NS
                        name = svc_namespace
                        index = 4

                    if index < 4:
                        print(f"check the output:{cfg}:{cmd}:{name}:")
                        print(f"output is: {out_lines}")
                        outcome = outcome & check_dry_run("server", cfg,
                                                          version, out_lines,
                                                          cmd, name)

                    out_lines = ""
                else:
                    out_lines = f"{out_lines}\n{line}" if out_lines else line

        else:
            print(f"[{FAIL}] no response received for dry-run test")
            outcome = False

    return outcome


def check_dry_run(dry_run_type, manifest_file, version, resp,
                  check_command, subject_name):

    if check_command == COMMAND_TENANT:
        manifest_yaml = get_manifest_yaml(manifest_file,
                                          version,
                                          PRIMAZA_CONFIG)
        expected_last_message = f"Dry run create primaza tenant " \
                                f"{subject_name} successfully completed"
    elif check_command == COMMAND_JOIN:
        manifest_yaml = get_manifest_yaml(manifest_file,
                                          version,
                                          WORKER_CONFIG)
        expected_last_message = f"Dry run join cluster {subject_name} " \
                                f"successfully completed"
    elif check_command == COMMAND_APP_NS:
        manifest_yaml = get_manifest_yaml(manifest_file,
                                          version,
                                          APP_AGENT_CONFIG)
        expected_last_message = f"Dry run create application namespace " \
                                f"{subject_name} successfully completed"
    elif check_command == COMMAND_SVC_NS:
        manifest_yaml = get_manifest_yaml(manifest_file,
                                          version,
                                          SVC_AGENT_CONFIG)
        expected_last_message = f"Dry run create service namespace " \
                                f"{subject_name} successfully completed"
    else:
        expected_last_message = "successfully completed"
        manifest_yaml = None

    if dry_run_type == "client":
        expect_lines = 0
    else:
        if manifest_yaml:
            expect_lines = len(list(manifest_yaml))
        else:
            expect_lines = 1

    outcome = True

    if not resp:
        outcome = False
        print(f"[{FAIL}] no response received for dry-run test")
    else:
        num_lines = 0
        last_line = 0
        for line in resp.splitlines():
            num_lines += 1
            if " (dry run) " not in line:
                if num_lines > expect_lines and expected_last_message in line:
                    last_line = num_lines
                else:
                    print(f"[{FAIL}] Unexpected line in response: {line} : "
                          f"Expected each line to contain: (dry run) ")
                    outcome = False

        if num_lines < expect_lines:
            print(f"[{FAIL}] response did not contain enough lines: "
                  f"{resp}")
            outcome = False
        elif num_lines > last_line:
            print(f"[{FAIL}] last line of response was not "
                  f"{expected_last_message}: {resp}")
            outcome = False

    return outcome


def test_output(command_args, dry_run_type=None):

    _, worker_resp = test_main_install(command_args.venv_dir,
                                       command_args.main_config,
                                       command_args.version,
                                       command_args.main_context,
                                       TENANT_FOR_OUTPUT,
                                       None, True, dry_run_type, "yaml")

    outcome = check_output(command_args.main_config,
                           command_args.version,
                           PRIMAZA_CONFIG, worker_resp)
    if outcome:
        print(f"[{PASS}] output yaml tenant install test passed. "
              f"dry-run={dry_run_type}")
    else:
        print(f"[{FAIL}] output yaml tenant install test failed. "
              f"dry-run={dry_run_type}")

    _, worker_resp = test_worker_install(
        command_args.venv_dir,
        command_args.worker_config,
        command_args.version,
        command_args.worker_context,
        command_args.main_context,
        TENANT_FOR_OUTPUT,
        command_args.service_account_namespace,
        None, None, True,
        dry_run_type, "yaml")

    worker_outcome = check_output(command_args.worker_config,
                                  command_args.version,
                                  WORKER_CONFIG, worker_resp)
    if worker_outcome:
        print(f"[{PASS}] output yaml worker join test passed. ",
              f"dry-run={dry_run_type}")
    else:
        print(f"[{FAIL}] output yaml worker join test failed. "
              f"dry-run={dry_run_type}")

    _, app_resp = test_application_namespace_create(
        command_args.venv_dir,
        APPLICATION_NAMESPACE_FOR_OUTPUT,
        command_args.worker_context,
        command_args.main_context,
        TENANT_FOR_OUTPUT,
        command_args.app_config,
        command_args.version,
        command_args.service_account_namespace,
        None, None, True, dry_run_type, "yaml")

    app_outcome = check_output(command_args.app_config,
                               command_args.version,
                               APP_AGENT_CONFIG, app_resp)
    if app_outcome:
        print(f"[{PASS}] output yaml application namespace create test "
              f"passed. dry-run={dry_run_type}")
    else:
        print(f"[{FAIL}] output yaml application namespace create test "
              f"failed. dry-run={dry_run_type}")

    _, service_resp = test_service_namespace_create(
        command_args.venv_dir,
        SERVICE_NAMESPACE_FOR_OUTPUT,
        command_args.worker_context,
        command_args.main_context,
        TENANT_FOR_OUTPUT,
        command_args.service_config,
        command_args.version,
        command_args.service_account_namespace,
        None, None, True, dry_run_type, "yaml")

    service_outcome = check_output(command_args.service_config,
                                   command_args.version,
                                   SVC_AGENT_CONFIG, service_resp)

    if service_outcome:
        print(f"[{PASS}] output yaml service namespace create test "
              f"passed. dry-run={dry_run_type}")
    else:
        print(f"[{FAIL}] output yaml service namespace create test "
              f"failed. dry-run={dry_run_type}")

    return outcome & worker_outcome & app_outcome & service_outcome


def check_output(manifest_file, version, type, resp):

    manifest_yaml = get_manifest_yaml(manifest_file, version, type)
    manifest_list = list(manifest_yaml)

    outcome = True
    response_yaml = yaml.safe_load(resp)
    for manifest_resource in manifest_list:
        match_found = False
        for response_resource in response_yaml["items"]:
            if response_resource["kind"] == manifest_resource["kind"]:
                if response_resource["metadata"]["name"] == \
                        manifest_resource["metadata"]["name"]:
                    match_found = True
                    break
        if not match_found:
            outcome = False
            print(f'{manifest_resource["kind"]} '
                  f'{manifest_resource["metadata"]["name"]} '
                  f'not found in response')

    return outcome


def test_apply(command_args):

    options_yaml = update_options_file(command_args)
    tenant = options_yaml["name"]
    cluster_options = options_yaml["clusterEnvironments"][0]
    sa_n = cluster_options.get("serviceAccountNamespace", None)
    cluster_env = cluster_options["name"]
    app_namespace = cluster_options["applicationNamespaces"][0]["name"]
    svc_namespace = cluster_options["serviceNamespaces"][0]["name"]

    if sa_n and sa_n != "kube-system":
        run_cmd(["kubectl", "create", "namespace",
                sa_n, "--context",
                cluster_options["targetCluster"]["context"]])

    with tempfile.NamedTemporaryFile(mode="w+") as options_file:
        with open(options_file.name, 'w') as options:
            yaml.dump(options_yaml, options)

        command = [f"{command_args.venv_dir}/bin/primazactl", "apply",
                   "-p", options_file.name]

        out, err = run_cmd(command)

        install_all_outcome = True
        if err:
            print(f"[{FAIL}] Unexpected error response: {err}")
            install_all_outcome = False
        elif out:
            if not check_apply_out(out, f"Create primaza tenant {tenant} "
                                        f"successfully completed"):
                install_all_outcome = False
            elif not check_apply_out(out, "Join cluster "
                                          f"{cluster_env} "
                                          "successfully completed"):
                install_all_outcome = False
            elif not check_apply_out(out, "Create application namespace "
                                          f"{app_namespace} "
                                          "successfully completed"):
                install_all_outcome = False
            elif not check_apply_out(out, "Create service namespace "
                                          f"{svc_namespace} "
                                          "successfully completed"):
                install_all_outcome = False
            elif not check_apply_out(out, "Primaza install from options "
                                          "file complete"):
                install_all_outcome = False
            else:
                print(f"[{PASS}] apply options file "
                      f"{command_args.options_file} passed")
        else:
            print(f"[{FAIL}] apply options file "
                  f"{command_args.options_file} did not produce any output")

    return install_all_outcome


def check_apply_out(out, expect_out):
    if expect_out not in out:
        print(f"[{FAIL}] Unexpected response: {out}. "
              f"Expected to contain {expect_out}")
        return False
    return True


def update_options_file(command_args):
    with open(command_args.options_file) as options:
        options_yaml = yaml.safe_load(options)

    main_url = get_cluster_internal_url(
        options_yaml['controlPlane']["context"].replace("kind-", ""))
    options_yaml['controlPlane']['internalUrl'] = main_url

    for cluster_environment in options_yaml["clusterEnvironments"]:
        target_cluster = cluster_environment["targetCluster"]
        worker_url = get_cluster_internal_url(target_cluster["context"].
                                              replace("kind-", ""))
        target_cluster["internalUrl"] = worker_url

    if command_args.version != "latest":
        options_yaml["version"] = command_args.version
        options_yaml["manifestDirectory"] = ""

    print(options_yaml)

    return options_yaml


def get_manifest_yaml(config_file, version, type):
    manifest = Manifest("", config_file,
                        version, type)
    return manifest.load_manifest()


def main():
    parser = argparse.ArgumentParser(
        prog='runtest',
        description='Run primazactl tests',
        epilog="Brought to you by the RedHat app-services team.")

    parser.add_argument("-p", "--venvdir",
                        dest="venv_dir", type=str, required=True,
                        help="location of python venv dir")
    parser.add_argument("-e", "--worker_config",
                        dest="worker_config", type=str, required=False,
                        help="worker config file.")
    parser.add_argument("-f", "--config",
                        dest="main_config", type=str, required=False,
                        help="main config file.")
    parser.add_argument("-c", "--worker_context",
                        dest="worker_context", type=str, required=False,
                        help="name of cluster, as it appears in kubeconfig, "
                             "on which to install worker")
    parser.add_argument("-m", "--main_context",
                        dest="main_context", type=str,
                        required=False,
                        help="name of cluster, as it appears in kubeconfig, "
                             "on which main is installed. "
                             "Defaults to worker install cluster.")
    parser.add_argument("-a", "--application_config",
                        dest="app_config", type=str, required=False,
                        help="application namespace config file.")
    parser.add_argument("-s", "--service_config",
                        dest="service_config", type=str, required=False,
                        help="service namespace config file.")
    parser.add_argument("-v", "--version",
                        dest="version", type=str, required=False,
                        help="primaza version to use.")
    parser.add_argument("-u", "--test-user",
                        dest="test_user",
                        required=False,
                        action="count",
                        help="Set to run test with users")
    parser.add_argument("-d", "--dry-run",
                        dest="dry_run",
                        required=False,
                        action="count",
                        help="Set to test dry-run")
    parser.add_argument("-o", "--output-yaml",
                        dest="output_yaml",
                        required=False,
                        action="count",
                        help="Set to test output yaml")
    parser.add_argument("-t", "--options-file",
                        dest="options_file",
                        required=False,
                        type=str,
                        help="Set to options file to run apply test")
    parser.add_argument("-i", "--input_dir",
                        dest="input_dir",
                        help="directory for kubeconfigs used for user tests",
                        required=False)
    parser.add_argument("-j", "--service-account-namespace",
                        dest="service_account_namespace",
                        required=False,
                        type=str,
                        help="namespace used for hosting the service account"
                             "shared with"
                             "Primaza's Control Plane(existing namespace).")
    parser.add_argument("-g", "--git-organization",
                        dest="git_org",
                        required=False,
                        type=str,
                        help="Githib organization, to obtain a release from, "
                             "when using version.")

    args = parser.parse_args()

    if args.git_org:
        os.environ[TEST_REPOSITORY_OVERRIDE] = f"{args.git_org}/primaza"

    if args.dry_run:
        outcome = test_dry_run(args, "client")
        outcome = outcome & test_dry_run(args, "server")
        if args.options_file:
            outcome = outcome & test_dry_run_with_options(args)
    elif args.output_yaml:
        outcome = test_output(args, "client")
        outcome = outcome & test_output(args)
    elif args.test_user:
        outcome = test_with_user(args)
    elif args.options_file:
        outcome = test_apply(args)
    else:
        outcome = test_args(args)
        outcome = outcome & test_create(args)

    if outcome:
        print(f"[{SUCCESS}] All tests passed")
    else:
        print(f"[{FAILED}] One or more tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
