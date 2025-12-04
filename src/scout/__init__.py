"""
Scout - Live Literature Intelligence for v2.1.

The Scout breaks the knowledge cutoff by fetching recent publications
from PubMed and grading evidence quality for injection into agent contexts.
"""

from src.scout.scout import run_scout

__all__ = ["run_scout"]

