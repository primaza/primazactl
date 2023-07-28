import yaml
import sys
from primazactl.utils import logger

dry_run = "none"
output_type = "none"
resources = {
    "apiVersion": "v1",
    "items": []
}
warnings = []

DRY_RUN_SERVER = "server"
DRY_RUN_CLIENT = "client"
DRY_RUN_NONE = "none"
DRY_RUN_CHOICES = [DRY_RUN_CLIENT, DRY_RUN_SERVER, DRY_RUN_NONE]

OUTPUT_YAML = "yaml"
OUTPUT_NONE = "none"
OUTPUT_CHOICES = [OUTPUT_YAML, OUTPUT_NONE]


def set(args):
    global dry_run
    global output_type

    if args.output_type != OUTPUT_NONE:
        output_type = args.output_type
    if args.dry_run != DRY_RUN_NONE:
        dry_run = args.dry_run
        logger.set_dry_run(" (dry run) ")
    logger.log_info(f"Dry run: {dry_run}, Dry run yaml output: {output_type}")


def dry_run_active():
    return dry_run != DRY_RUN_NONE


def output_active():
    return output_type != OUTPUT_NONE


def output():
    if output_type == OUTPUT_YAML:
        print(f"\n{yaml.dump(resources)}")
        if len(warnings) > 0:
            for warning in warnings:
                print(warning, file=sys.stderr)


def add_resource(resource):
    global resources
    if output_active():
        resources["items"].append(resource)


def add_warning(message):
    global warnings
    if output_active():
        warnings.append(f"WARNING:{dry_run}{message}")
    logger.log_warning(message)
