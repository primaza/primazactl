from primazactl.cmd.worker.join import add_join


def add_group(subparsers, parents=[]):
    worker_group = subparsers.add_parser(
        name="worker",
        help="Operations on main Worker cluster",
        parents=parents)
    worker_subparsers = worker_group.add_subparsers()

    add_join(worker_subparsers, parents=parents)
