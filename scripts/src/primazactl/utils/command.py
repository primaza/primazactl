import subprocess
import time
import os
from primazactl.utils import logger


class Command(object):
    path = ""
    env = {}

    def __init__(self, path=None):
        if path is None:
            self.path = os.getcwd()
        else:
            self.path = path

        path = os.getenv("PATH")
        assert path is not None, "PATH needs to be set in the environment"
        self.setenv("PATH", path)

    def setenv(self, key, value):
        assert key is not None and value is not None, \
            f"Name or value of the environment variable cannot be None:" \
            f" [{key} = {value}]"
        self.env[key] = value
        logger.log_info(f"command env set: [{key} = {value}]")
        return self

    def run(self, cmd, stdin=None):
        # for debugging purposes
        logger.log_entry(f"COMMAND : {cmd}")
        if stdin is not None:
            logger.log_entry("get input from stdin")
        exit_code = 0
        try:
            if stdin is None:
                output = subprocess.check_output(cmd, shell=True,
                                                 stderr=subprocess.STDOUT,
                                                 cwd=self.path, env=self.env)
            else:
                output = subprocess.check_output(cmd, shell=True,
                                                 stderr=subprocess.STDOUT,
                                                 cwd=self.path, env=self.env,
                                                 input=stdin.encode("utf-8"))
        except subprocess.CalledProcessError as err:
            output = err.output
            exit_code = err.returncode
            logger.log_error(f'MESSAGE: {output}')
            logger.log_error(f'ERROR CODE: {exit_code}')
        return output.decode("utf-8"), exit_code

    def run_wait_for_status(self, cmd, status, interval=20, timeout=180):
        cmd_output = None
        exit_code = -1
        start = 0
        while ((start + interval) <= timeout):
            cmd_output, exit_code = self.run(cmd)
            if status in cmd_output:
                return True, cmd_output, exit_code
            time.sleep(interval)
            start += interval
        logger.log_error("Time out while waiting for status message.")
        return False, cmd_output, exit_code
