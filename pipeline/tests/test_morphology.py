import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.morphology import *
CATALOG={
 "hair_short":{"slot":"hair","name":"Short Hair"},
 "helmet_scout":{"slot":"headwear","name":"Scout Helmet"},
 "backpack_field":{"slot":"back","name":"Field Backpack"},
 "armor_chest":{"slot":"torso","name":"Chest Armor"}
}
class MorphologyTests(unittest.TestCase):
 def test_face_profile_is_deterministic(self):
  self.assertEqual(seeded_face_profile("FG-HUM-000001",123),seeded_face_profile("FG-HUM-000001",123))
 def test_seed_changes_profile(self):
  self.assertNotEqual(seeded_face_profile("FG-HUM-000001",123),seeded_face_profile("FG-HUM-000001",124))
 def test_control_range_and_unknown(self):
  self.assertEqual(clamp_controls({"jaw_width":1.2},FACE_CONTROLS)["jaw_width"],1.2)
  with self.assertRaises(ValueError): clamp_controls({"jaw_width":2},FACE_CONTROLS)
  with self.assertRaises(ValueError): clamp_controls({"third_eye":1},FACE_CONTROLS)
 def test_modules_allow_distinct_slots(self):
  self.assertEqual(len(validate_modules(["hair_short","helmet_scout","backpack_field"],CATALOG)),3)
 def test_module_slot_conflict(self):
  with self.assertRaises(ValueError): validate_modules(["hair_short","helmet_scout","armor_chest"],CATALOG)
 def test_species_compatibility(self):
  with self.assertRaises(ValueError): validate_modules(["hair_short"],CATALOG,species="robot")
 def test_duplicate_module_rejected(self):
  with self.assertRaises(ValueError): validate_modules(["hair_short","hair_short"],CATALOG)
if __name__=="__main__": unittest.main()
