"Лабораторна робота 1."

import os
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
)

from labs.lab01 import task1, task2, task3  # noqa: E402

if __name__ == "__main__":
    task1.main()
    task2.main()
    task3.main()
