import sys

from calcapp.formatter import format_result
from calcapp.operations import calculate


def main(argv):
    if len(argv) != 4:
        print("usage: python app.py <add|subtract|multiply|mul> <a> <b>")
        return 1

    operation = argv[1]
    a = float(argv[2])
    b = float(argv[3])
    result = calculate(operation, a, b)
    print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))