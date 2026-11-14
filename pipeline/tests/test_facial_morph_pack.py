import unittest
from pathlib import Path
import runpy

SCRIPT=Path(__file__).resolve().parents[1]/"blender"/"facial_morph_pack.py"
ns=runpy.run_path(str(SCRIPT))
class FacialMorphMathTests(unittest.TestCase):
    def test_front_surface_weight_is_bounded(self):
        from mathutils import Vector
        self.assertGreater(ns["face_weight"](Vector((0,-.2,0))),0.9)
        self.assertEqual(ns["face_weight"](Vector((0,.2,0))),0.0)
    def test_all_targets_produce_finite_deltas(self):
        from mathutils import Vector
        for name in list(ns["EXPRESSIONS"].values())+list(ns["VISEME"].values()):
            value=ns["delta"](name,Vector((.05,-.2,-.1)))
            self.assertEqual(len(value),3)
            self.assertTrue(all(abs(v)<1 for v in value))
if __name__=="__main__": unittest.main()
