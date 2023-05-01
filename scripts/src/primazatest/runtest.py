import argparse
import subprocess
import sys
import time

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'


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
                print(f"\n---[{FAIL}] args: {args} : {fail_msg}\n")
                outcome = False
        else:
            print(f"\n---[{FAIL}] args: {args} : {fail_msg}")
            outcome = False

    return outcome


def test_args(venv_dir):

    outcome = True
    expect_msg = "usage: primazactl [-h]"
    fail_msg = "unexpected response to no arguments"
    outcome = outcome & run_and_check(venv_dir, None, expect_msg,
                                      None, fail_msg)

    args = ["main"]
    expect_msg = "usage: primazactl [-h]"
    fail_msg = "unexpected response to single argument"
    outcome = outcome & run_and_check(venv_dir, args, expect_msg,
                                      None, fail_msg)

    args = ["drink"]
    expect_error_msg = "error: argument {main,worker}: " \
        "invalid choice: 'drink' (choose from 'main', 'worker')"
    fail_msg = "unexpected response invalid action"
    outcome = outcome & run_and_check(venv_dir, args, None,
                                      expect_error_msg, fail_msg)

    args = ["main", "install", "-k", "/.kube/DoesNotExist"]
    expect_error_msg = "error: argument -k/--kubeconfig: --config does not" \
                       " specify a valid file: /.kube/DoesNotExist"
    fail_msg = "unexpected response to bad kube config file"
    outcome = outcome & run_and_check(venv_dir, args, None,
                                      expect_error_msg, fail_msg)

    args = ["main", "install", "-f", "scripts/config/DoesNotExist"]
    expect_error_msg = "error: argument -f/--config: --config does not " \
                       "specify a valid file: scripts/config/DoesNotExist"
    fail_msg = "unexpected response to bad config file"
    outcome = outcome & run_and_check(venv_dir, args, None,
                                      expect_error_msg, fail_msg)

    args = ["main", "install", "-v", "version.not.semantic"]
    expect_error_msg = "error: argument -v/--version: --version is not a" \
                       " valid semantic version: version.not.semantic"
    fail_msg = "unexpected response to bad version"
    outcome = outcome & run_and_check(venv_dir, args, None,
                                      expect_error_msg, fail_msg)

    args = ["main",
            "install",
            "-c",
            "non-existent-cluster",
            "--config",
            "out/config/primaza_config_latest.yaml"]
    expect_error_msg = "error deploying Primaza's controller" \
                       " into cluster non-existent-cluster"
    fail_msg = "unexpected response to bad cluster"
    outcome = outcome & run_and_check(venv_dir, args, None,
                                      expect_error_msg, fail_msg)

    return outcome


def test_main_install(venv_dir, config, cluster):

    command = [f"{venv_dir}/bin/primazactl",
               "main",
               "install",
               "-f", config,
               "-c", cluster]
    out, err = run_cmd(command)

    if err:
        print(f"[{FAIL}] Unexpected error response: {err}")
        return False

    if "Primaza main installed" not in out:
        print(f"[{FAIL}] Unexpected response: {out}")
        return False

    if not check_pods(cluster, "primaza-system"):
        print(f"[{FAIL}] main install pod is not running: {out}")
        return False

    print(f"[{PASS}] main install was successful.")
    return True


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


def test_worker_install(venv_dir, config, worker_cluster, main_cluster):

    command = [f"{venv_dir}/bin/primazactl",
               "worker", "join",
               "-e", "test",
               "-d", "primaza-environment",
               "-f", config,
               "-c", worker_cluster,
               "-m", main_cluster]

    out, err = run_cmd(command)
    if err:
        print(f"[{FAIL}] Unexpected error response: {err}")
        return False

    if "Install and configure worker completed" not in out:
        print(f"[{FAIL}] Unexpected response: {out}")
        return False

    return True


def test_application_namespace_create(venv_dir, worker_cluster,
                                      main_cluster, config):

    command = [f"{venv_dir}/bin/primazactl",
               "worker", "create", "application-namespace",
               "-d", "primaza-environment",
               "-c", worker_cluster,
               "-m", main_cluster,
               "-f", config]

    out, err = run_cmd(command)
    if err:
        print(f"[{FAIL}] Unexpected error response: {err}")
        return False

    if "was successfully created" not in out:
        print(f"[{FAIL}] Unexpected response: {out}")
        return False

    if not check_pods(worker_cluster, "primaza-application"):
        print(f"[{FAIL}] application namespace pod is not running!\n\n{out}")
        return False

    print(f"[{PASS}] Application namespace created\n\n{out}")
    return True


def test_service_namespace_create(venv_dir, worker_cluster,
                                  main_cluster, config):

    command = [f"{venv_dir}/bin/primazactl",
               "worker", "create", "service-namespace",
               "-d", "primaza-environment",
               "-c", worker_cluster,
               "-m", main_cluster,
               "-f", config]

    out, err = run_cmd(command)
    if err:
        print(f"[{FAIL}] Unexpected error response: {err}")
        return False

    if "was successfully created" not in out:
        print(f"[{FAIL}] Unexpected response: {out}")
        return False

    if not check_pods(worker_cluster, "primaza-service"):
        print(f"[{FAIL}] service namespace pod is not running!\n\n{out}")
        return False

    print(f"[{PASS}] Service namespace created\n\n{out}")
    return True


def main():
    parser = argparse.ArgumentParser(
        prog='runtest',
        description='Run primazactl tests',
        epilog="Brought to you by the RedHat app-services team.")

    parser.add_argument("-v", "--venvdir",
                        dest="venv_dir", type=str, required=True,
                        help="location of python venv dir")
    parser.add_argument("-e", "--worker_config",
                        dest="worker_config", type=str, required=True,
                        help="worker config file.")
    parser.add_argument("-f", "--config",
                        dest="main_config", type=str, required=True,
                        help="main config file.")
    parser.add_argument("-c", "--worker_cluster_name",
                        dest="worker_cluster_name", type=str, required=True,
                        help="name of cluster, as it appears in kubeconfig, "
                             "on which to install worker")
    parser.add_argument("-m", "--mainclustername",
                        dest="main_cluster_name", type=str,
                        required=True,
                        help="name of cluster, as it appears in kubeconfig, "
                             "on which main is installed. "
                             "Defaults to worker install cluster.")
    parser.add_argument("-a", "--application_config",
                        dest="app_config", type=str, required=True,
                        help="application namespace config file.")
    parser.add_argument("-s", "--service_config",
                        dest="service_config", type=str, required=True,
                        help="service namespace config file.")

    args = parser.parse_args()

    outcome = test_args(args.venv_dir)
    outcome = outcome & test_main_install(args.venv_dir, args.main_config,
                                          args.main_cluster_name)
    outcome = outcome & test_worker_install(args.venv_dir,
                                            args.worker_config,
                                            args.worker_cluster_name,
                                            args.main_cluster_name)
    outcome = outcome & test_application_namespace_create(
        args.venv_dir,
        args.worker_cluster_name,
        args.main_cluster_name,
        args.app_config)
    outcome = outcome & test_service_namespace_create(
        args.venv_dir,
        args.worker_cluster_name,
        args.main_cluster_name,
        args.service_config)

    if outcome:
        print("[SUCCESS] All tests passed")
    else:
        print("[FAILED] One or more tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
