import os


def expand_path(path):
    new_path = os.path.expanduser(path)
    return os.path.abspath(new_path)
