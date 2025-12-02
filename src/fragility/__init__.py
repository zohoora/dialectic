"""
Fragility Testing module.

Stress-tests consensus recommendations by applying perturbations
to identify conditions under which recommendations break.
"""

from src.fragility.perturbation_generator import PerturbationGenerator
from src.fragility.tester import FragilityTester

__all__ = ["FragilityTester", "PerturbationGenerator"]
