"""Entry point executed by PyTauri's embedded interpreter.

PyTauri starts the Python side with ``python -m finance_app`` which executes
this file as ``__main__``.  Therefore it must use an absolute import.
"""

from finance_app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
