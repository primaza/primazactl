from typing import Iterable


class ValidationError(Exception):
    pass


class AtLeastOneError(ValidationError):
    args = []

    def __init__(self, *args: Iterable[str]):
        self.args = args

    def __str__(self):
        return "at least one among " + ",".join(self.args) + " is required"
