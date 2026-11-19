from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]

class AuthContractTests(unittest.TestCase):
    def test_frontend_has_accessible_auth_controls(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        for marker in (
            'id="authButton"', 'id="authModal"', 'role="dialog"',
            'id="authEmail"', 'id="authPassword"', 'id="authConfirm"',
            'id="authSignupLink"', 'id="authResetLink"', 'src="./auth.js"',
        ):
            self.assertIn(marker, html)

    def test_auth_uses_supabase_auth_and_no_service_role(self):
        auth = (ROOT / "auth.js").read_text(encoding="utf-8")
        for marker in (
            "signUp(", "signInWithPassword(", "resetPasswordForEmail(",
            "onAuthStateChange(", "persistSession: true", "autoRefreshToken: true",
            'from("saved_presets")', "forge:preset-saved",
        ):
            self.assertIn(marker, auth)
        self.assertNotIn("service_role", auth.lower())
        self.assertNotIn("SERVICE_ROLE", auth)

    def test_supabase_schema_enforces_per_user_isolation(self):
        sql = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8").lower()
        self.assertIn("enable row level security", sql)
        self.assertIn("(select auth.uid()) = user_id", sql)
        self.assertIn("(select auth.uid()) = id", sql)
        self.assertIn("on delete cascade", sql)
        self.assertNotRegex(sql, r"using\s*\(\s*true\s*\)")

    def test_public_config_is_explicitly_unconfigured(self):
        config = (ROOT / "supabase-config.js").read_text(encoding="utf-8")
        self.assertIn("YOUR_PROJECT_REF", config)
        self.assertIn("YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY", config)
        self.assertNotIn("service_role", config.lower())

if __name__ == "__main__":
    unittest.main()
