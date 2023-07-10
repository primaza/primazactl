import argparse
import sys
from primazactl import parser
from primazactl.errors import ValidationError
from primazactl.utils import logger


def main():
    p = parser.build_parser()

    try:
        args = p.parse_args()

        if hasattr(args, "verbose"):
            logger.set_verbose(args.verbose)

        if not hasattr(args, "func"):
            p.print_help()
            return

        args.func(args)
        sys.exit(0)

    except (argparse.ArgumentError, ValidationError) as err:
        p.error(err)
    except Exception:
        # arparse will output an error
        pass

    sys.exit(1)


if __name__ == "__main__":
    main()
