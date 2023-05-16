import sys
from subprocess import run
from typing import IO


class tee:
    """Performs file-like I/O operations between several targets."""

    def __init__(self, *targets: IO):
        self._targs = list(targets)

    def __del__(self):
        for targ in self._targs:
            if targ not in [sys.stdin, sys.stderr]:
                targ.close()

    def write(self, text):
        for targ in self._targs:
            targ.write(text)

    def flush(self):
        for targ in self._targs:
            targ.flush()


with open("scratch.txt", "w") as file_a, open("scratch_b.txt", "w") as file_b:
    myTee: tee = tee(sys.stdout, file_a, file_b)
    run(  # type: ignore
        ["echo", "\"Hello,", "World!\""], stdout=myTee, text=True, check=True)
