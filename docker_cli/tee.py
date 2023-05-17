import sys
from subprocess import run
from typing import IO


class tee(object):
    """Performs file-like I/O operations between several targets."""

    def __init__(self, *targets: IO):
        self.sys_stdout = sys.stdout
        sys.stdout = self   # type: ignore
        self._targs = list(targets)

    def __del__(self):
        sys.stdout = self.sys_stdout
        for targ in self._targs:
            if targ not in [sys.stdout, sys.stderr]:
                targ.close()

    def remove(self):
        sys.stdout = self.sys_stdout
        """for targ in self._targs:
            if targ not in [sys.stdin, sys.stderr]:
                targ.close()"""

    def write(self, text):
        for targ in self._targs:
            if targ is not self.sys_stdout:
                with open(file=targ.name, mode="a", encoding=targ.encoding) as f:
                    f.write(text)
                    f.flush()
            else:
                targ.write(text)

    def flush(self):
        for targ in self._targs:
            if targ is not self.sys_stdout:
                with open(file=targ.name, mode="a", encoding=targ.encoding) as f:
                    f.flush()
            else:
                targ.flush()


with open("scratch.txt", "w") as file_a, open("scratch_b.txt", "w") as file_b:
    myTee: tee = tee(sys.stdout, file_a, file_b)
    print("preprint\n", flush=True)
    run(  # type: ignore
        ["echo", "\"Hello,", "World!\""], text=True, check=True)
print("wee")
myTee.remove()
del myTee
print("yee")
