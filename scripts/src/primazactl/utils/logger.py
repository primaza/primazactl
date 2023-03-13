import inspect

verbose = False


def log_info(message, always=False):
    if always:
        print(f"{message}")
    elif verbose:
        stack = inspect.stack()
        if "self" in stack[1][0].f_locals:
            calling_class = stack[1][0].f_locals["self"].__class__.__name__
        else:
            calling_class = ""
        calling_method = stack[1][0].f_code.co_name
        print(f"[INFO]  {calling_class}.{calling_method} : {message}")


def log_entry(message="Just entering"):
    if verbose:
        __write_log("[ENTER]", message)


def log_exit(message="Just exiting"):
    if verbose:
        __write_log("[EXIT] ", message)


def log_error(message):
    if verbose:
        __write_log("[ERROR]", message)
    else:
        print(f"[ERROR] {message}")


def set_verbose(value):
    global verbose
    verbose = value


def __write_log(type, message):
    stack = inspect.stack()
    calling_class = stack[2][0].f_locals["self"].__class__.__name__
    calling_method = stack[2][0].f_code.co_name
    print(f"{type} {calling_class}.{calling_method} : {message}")
