import yaml
import sys
from primazactl.utils import logger

dry_run = False
output_yaml = False
resources = {
    "apiVersion": "v1",
    "items": []
}
warnings = []


def set(args):
    global dry_run
    global output_yaml

    if args.output_yaml == "yaml":
        output_yaml = True
    if args.dry_run:
        dry_run = True
    logger.log_info(f"Dry run: {dry_run}, Dry run yaml output: {output_yaml}")


def get_dry_run():
    if dry_run:
        return " (dry run) "
    else:
        return ""


def output():
    if output_yaml:
        print(f"\n{yaml.dump(resources)}")
        if len(warnings) > 0:
            for warning in warnings:
                print(warning, file=sys.stderr)


def add_resource(resource):
    global resources
    if output_yaml:
        resources["items"].append(resource)


def add_warning(message):
    global warnings
    if output_yaml:
        warnings.append(f"WARNING:{get_dry_run()}{message}")
    logger.log_warning(message)
