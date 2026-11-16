"""Blender-hosted tests for Forge cloth triangle narrow-phase QA."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pipeline.blender.cloth_integrity_qa import triangles_intersect

BASE = ((0, 0, 0), (1, 0, 0), (0, 1, 0))
CASES = (
    ("non_coplanar_crossing", ((0.2, 0.2, -1), (0.2, 0.2, 1), (0.8, 0.2, 0)), True),
    ("parallel_separated", ((0, 0, 1), (1, 0, 1), (0, 1, 1)), False),
    ("coplanar_overlap", ((0.2, 0.2, 0), (0.8, 0.2, 0), (0.2, 0.8, 0)), True),
    ("coplanar_separated", ((2, 2, 0), (3, 2, 0), (2, 3, 0)), False),
    ("coplanar_edge_contact", ((1, 0, 0), (1, 1, 0), (0, 1, 0)), True),
)

for name, triangle, expected in CASES:
    actual = triangles_intersect(BASE, triangle)
    if actual is not expected:
        raise AssertionError("%s: expected %s, got %s" % (name, expected, actual))

print("FORGE_TRIANGLE_INTERSECTION_TESTS_PASSED cases=%d" % len(CASES))
