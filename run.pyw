"""Start Remind Me without a console window:  pythonw run.pyw"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from remindme.app import main  # noqa: E402

if __name__ == "__main__":
    main()
