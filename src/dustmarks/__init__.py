"""Find TODO-style comments in a git repository and see how long they have waited."""

from dustmarks.core import Mark, scan
from dustmarks.git import GitError

__all__ = ["GitError", "Mark", "__version__", "scan"]
__version__ = "0.1.0"
