import inspect
import os
from primazactl.version import __version__, __primaza_version__

verbose = False
first_log = True
dry_run: str = ""


def set_dry_run(dry_run_text):
    global dry_run
    dry_run = dry_run_text


def log_info(message, always=False):
    if always:
        print(f"[INFO]{dry_run}{message}")
    elif verbose:
        __write_log(f"[INFO]{dry_run}", message)


def log_entry(message="Just entering"):
    if verbose:
        __write_log("[ENTER]", message)


def log_exit(message="Just exiting"):
    if verbose:
        __write_log("[EXIT] ", message)


def log_warning(message):
    if verbose:
        __write_log(f"[WARNING]{dry_run}", message)


def log_error(message, always=True):

    if always:
        print(f"[ERROR]{dry_run}{message}")
    elif verbose:
        __write_log(f"[ERROR]{dry_run}", message)


def set_verbose(value):
    global verbose
    verbose = value


def __write_log(type, message):
    global first_log
    if first_log:
        first_log = False
        log_info(f"Primazactl version: {__version__}, "
                 f"Primaza version: {__primaza_version__}")
    stack = inspect.stack()
    if "self" in stack[2][0].f_locals:
        calling_class = stack[2][0].f_locals["self"].__class__.__name__
        calling_method = stack[2][0].f_code.co_name
        print(f"{type} {calling_class}.{calling_method} : {message}")
    else:
        calling_file = os.path.basename(stack[2].filename)
        calling_method = stack[2].function
        print(f"{type} {calling_file}:{calling_method} : {message}")
