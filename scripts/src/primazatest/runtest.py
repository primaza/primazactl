import argparse
import subprocess
import sys
import time
import os

PASS = '\033[92mPASS\033[0m'
SUCCESS = '\033[92mSUCCESS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
FAILED = '\033[91mFAILED\033[0m'

TENANT = "primaza-controller-system"
SERVICE_NAMESPACE = "service-agent-system"
APPLICATION_NAMESPACE = "application-agent-system"


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
    expect_error_msg = "error: argument {create,delete,join}: " \
        "invalid choice: 'drink' (choose from 'create', 'delete', 'join')"
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
                      cluster, namespace, kubeconfig=None, expect_out=False):

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

    out, err = run_cmd(command)

    if out and expect_out:
        return True, out

    if err:
        print(f"[{FAIL}] Unexpected error response: {err}")
        return False, None

    if "Primaza main installed" not in out:
        print(f"[{FAIL}] Unexpected response: {out}")
        return False, None

    if not check_pods(cluster, namespace):
        print(f"[{FAIL}] main install pod is not running: {out}")
        return False, None

    print(f"[{PASS}] main installed.")
    return True, None


def check_pods(cluster, namespace):
    outcome = True
    for i in range(1, 60):

        pods, err = run_cmd(["kubectl", "get", "pods", "-n",
                             namespace, "--context",
                             cluster], 1 < i < 60)

        if pods:
            if "Running" in pods and "2/2" in pods:
                print(pods)
                break
            elif "ErrImagePull" in pods or "ImagePullBackOff" in pods:
                print(pods)
                outcome = False
                break
            elif i == 60:
                print("---[{FAIL}]: Pods not running after 120s")
                print(pods)
                outcome = False
        if err:
            print(f"---[{FAIL}]: {err}")
            outcome = False
            break
        time.sleep(2)

    if not outcome:
        time.sleep(5)
        pods, err = run_cmd(["kubectl", "describe",
                             "pods", "-n", namespace,
                             "--context", cluster])
        if pods:
            print(pods)
        if err:
            print(err)

    return outcome


def test_worker_install(venv_dir, config, version, worker_cluster,
                        main_cluster, tenant, kubeconfig=None,
                        main_kubeconfig=None, expect_out=False):

    if version:
        command = [f"{venv_dir}/bin/primazactl",
                   "join", "cluster",
                   "-e", "test",
                   "-d", "primaza-environment",
                   "-c", worker_cluster,
                   "-m", main_cluster,
                   "-t", tenant,
                   "-v", version]
    else:
        command = [f"{venv_dir}/bin/primazactl",
                   "join", "cluster",
                   "-e", "test",
                   "-d", "primaza-environment",
                   "-c", worker_cluster,
                   "-m", main_cluster,
                   "-t", tenant,
                   "-f", config]

    if kubeconfig:
        command.append("-k")
        command.append(kubeconfig)
    if main_kubeconfig:
        command.append("-l")
        command.append(main_kubeconfig)

    out, err = run_cmd(command)

    if out and expect_out:
        return True, out

    if err:
        print(f"[{FAIL}] Unexpected error response: {err}\n{out}")
        return False, None

    if "Install and configure worker completed" not in out:
        print(f"[{FAIL}] Unexpected response: {out}")
        return False, None

    print(f"[{PASS}] Worker joined\n\n{out}")
    return True, None


def test_application_namespace_create(venv_dir, namespace,
                                      worker_cluster,
                                      main_cluster, tenant,
                                      config, version,
                                      kubeconfig=None,
                                      main_kubeconfig=None,
                                      expect_out=False):
    if version:
        command = [f"{venv_dir}/bin/primazactl",
                   "create", "application-namespace",
                   namespace,
                   "-d", "primaza-environment",
                   "-c", worker_cluster,
                   "-m", main_cluster,
                   "-t", tenant,
                   "-v", version]
    else:
        command = [f"{venv_dir}/bin/primazactl",
                   "create", "application-namespace",
                   namespace,
                   "-d", "primaza-environment",
                   "-c", worker_cluster,
                   "-m", main_cluster,
                   "-t", tenant,
                   "-f", config]

    if kubeconfig:
        command.append("-k")
        command.append(kubeconfig)
    if main_kubeconfig:
        command.append("-l")
        command.append(main_kubeconfig)

    out, err = run_cmd(command)
    if out and expect_out:
        return True, out

    if err:
        print(f"[{FAIL}] Unexpected error response: {err}")
        return False, None

    if "was successfully created" not in out:
        print(f"[{FAIL}] Unexpected response: {out}")
        return False, None

    if not check_pods(worker_cluster, namespace):
        print(f"[{FAIL}] application namespace pod is not running!\n\n{out}")
        return False, None

    print(f"[{PASS}] Application namespace created\n\n{out}")
    return True, None


def test_service_namespace_create(venv_dir, namespace,
                                  worker_cluster,
                                  main_cluster, tenant,
                                  config,
                                  version, kubeconfig=None,
                                  main_kubeconfig=None,
                                  expect_out=False):

    if version:
        command = [f"{venv_dir}/bin/primazactl",
                   "create", "service-namespace",
                   namespace,
                   "-d", "primaza-environment",
                   "-c", worker_cluster,
                   "-m", main_cluster,
                   "-t", tenant,
                   "-v", version]
    else:
        command = [f"{venv_dir}/bin/primazactl",
                   "create", "service-namespace",
                   namespace,
                   "-d", "primaza-environment",
                   "-c", worker_cluster,
                   "-m", main_cluster,
                   "-t", tenant,
                   "-f", config]

    if kubeconfig:
        command.append("-k")
        command.append(kubeconfig)
    if main_kubeconfig:
        command.append("-l")
        command.append(main_kubeconfig)

    out, err = run_cmd(command)

    if out and expect_out:
        return True, out

    if err:
        print(f"[{FAIL}] Unexpected error response: {err}")
        return False, None

    if "was successfully created" not in out:
        print(f"[{FAIL}] Unexpected response: {out}")
        return False, None

    if not check_pods(worker_cluster, namespace):
        print(f"[{FAIL}] service namespace pod is not running!\n\n{out}")
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
    bad_outcome, out = test_worker_install(command_args.venv_dir,
                                           command_args.worker_config,
                                           command_args.version,
                                           command_args.worker_context,
                                           command_args.main_context,
                                           TENANT, bad_kubeconfig,
                                           main_kubeconfig, True)
    if expect_out in out:
        print(f"[{PASS}] Output includes expected text: {expect_out}")
    else:
        print(f"[{FAIL}] Unexpected response: {out}. "
              f"Expected to contain {expect_out}")
        bad_outcome = False

    worker_kubeconfig = os.path.join(configs_dir, "worker-kube.config")
    good_outcome, _ = test_worker_install(command_args.venv_dir,
                                          command_args.worker_config,
                                          command_args.version,
                                          command_args.worker_context,
                                          command_args.main_context,
                                          TENANT, worker_kubeconfig,
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
    worker_outcome, _ = test_worker_install(command_args.venv_dir,
                                            command_args.worker_config,
                                            command_args.version,
                                            command_args.worker_context,
                                            command_args.main_context,
                                            TENANT)
    outcome = outcome & worker_outcome
    app_outcome, _ = test_application_namespace_create(
        command_args.venv_dir,
        APPLICATION_NAMESPACE,
        command_args.worker_context,
        command_args.main_context,
        TENANT,
        command_args.app_config,
        command_args.version)
    outcome = outcome & app_outcome

    svc_outcome, _ = test_service_namespace_create(
        command_args.venv_dir,
        SERVICE_NAMESPACE,
        command_args.worker_context,
        command_args.main_context,
        TENANT,
        command_args.service_config,
        command_args.version)

    return outcome & svc_outcome


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
                        dest="worker_context", type=str, required=True,
                        help="name of cluster, as it appears in kubeconfig, "
                             "on which to install worker")
    parser.add_argument("-m", "--main_context",
                        dest="main_context", type=str,
                        required=True,
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
    parser.add_argument("-i", "--input_dir",
                        dest="input_dir",
                        help="directory for kubeconfigs used for user tests",
                        required=False)

    args = parser.parse_args()

    if args.test_user:
        outcome = test_with_user(args)
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
