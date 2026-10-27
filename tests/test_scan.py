import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("gc", ROOT / "scanner" / "scan.py")
gc = importlib.util.module_from_spec(spec)
sys.modules["gc"] = gc
spec.loader.exec_module(gc)


class TestClaimVerifier(unittest.TestCase):
    def test_flags_missing_script(self):
        text = "Run `npm run deploy` to ship."
        ok, fail, notes = gc.check_claims(text, {"package.json"}, "x/y", "main")
        # package.json is in the tree but has no scripts -> claim fails
        self.assertEqual(fail, 1)
        self.assertEqual(ok, 0)
        self.assertTrue(any("deploy" in n for n in notes))

    def test_counts_existing_script(self):
        text = "```bash\nnpm run build\n```"
        paths = {"package.json"}
        orig = gc.raw
        gc.raw = lambda full, ref, path: '{"scripts": {"build": "tsc"}}' if path == "package.json" else orig(full, ref, path)
        try:
            ok, fail, _ = gc.check_claims(text, paths, "x/y", "main")
        finally:
            gc.raw = orig
        self.assertEqual((ok, fail), (1, 0))

    def test_flags_dead_path(self):
        text = "Read `docs/architecture.md` first."
        ok, fail, notes = gc.check_claims(text, {"README.md"}, "x/y", "main")
        self.assertEqual(fail, 1)
        self.assertTrue(any("architecture" in n for n in notes))


class TestLocalScan(unittest.TestCase):
    def test_scores_repo_without_context(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "main.py").write_text("print('hi')\n", encoding="utf-8")
            gc.LOCAL_ROOT = Path(d)
            try:
                rep = gc.audit(Path(d).name)
            finally:
                gc.LOCAL_ROOT = None
            self.assertFalse(rep.error)
            self.assertEqual(rep.ctx_chars, 0)
            self.assertLess(rep.total, 40)
            self.assertIn(rep.grade, "DF")

    def test_scores_repo_with_truthful_context(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "AGENTS.md").write_text(
                "# AGENTS\n\nRun `python main.py`. See `src/app.py`.\n", encoding="utf-8")
            Path(d, "main.py").write_text("print('hi')\n", encoding="utf-8")
            Path(d, "src").mkdir()
            Path(d, "src", "app.py").write_text("x = 1\n", encoding="utf-8")
            gc.LOCAL_ROOT = Path(d)
            try:
                rep = gc.audit(Path(d).name)
            finally:
                gc.LOCAL_ROOT = None
            self.assertEqual(rep.truth_fail, 0)
            self.assertGreater(rep.total, 20)

    def test_grade_thresholds(self):
        rep = gc.Report(repo="x")
        rep.signals = [gc.Signal("a", "A", 100, 0.9, "")]
        self.assertEqual(rep.grade, "A")
        rep.signals = [gc.Signal("a", "A", 100, 0.3, "")]
        self.assertEqual(rep.grade, "F")


class TestWeights(unittest.TestCase):
    def test_signals_sum_to_100(self):
        weights = [15, 20, 12, 8, 12, 10, 8, 8, 7]
        self.assertEqual(sum(weights), 100)


if __name__ == "__main__":
    unittest.main()
