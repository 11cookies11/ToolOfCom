from __future__ import annotations

import argparse
import sys

from runtime.runner import run_dsl


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ProtoFlow DSL 执行入口")
    parser.add_argument("script", help="DSL YAML 文件路径")
    args = parser.parse_args(argv)
    return run_dsl(args.script)


if __name__ == "__main__":
    sys.exit(main())
