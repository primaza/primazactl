import os
import re
import semver
from argparse import ArgumentTypeError


def existing_file(arg):
    if not os.path.isfile(arg):
        raise ArgumentTypeError(
            f"--config does not specify a valid file: {arg}")

    return arg


def semvertag_or_latest(arg):
    if arg != "latest" and arg != "nightly":
        version = arg[1:] if arg.startswith("v") else arg
        if not semver.VersionInfo.isvalid(version):
            raise ArgumentTypeError(
                f"--version is not a valid semantic version: {arg}")
    return arg


def kubernetes_name(arg):
    pattern = re.compile("^(([a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9]).)*"
                         "([a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])$")
    if not pattern.match(arg):
        print("\n[ERROR] value must consist of lower case alphanumeric "
              "characters, \'-\' or \'.\', and must start and end with "
              "an alphanumeric character\n")
        raise ArgumentTypeError(
            f"--version is not a valid kubernetes context name: {arg}")

    return arg
