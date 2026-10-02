"""兩類「整體」測試：模組依賴規則（第 23 章），以及三個端到端範例能跑完。"""
import ast
import contextlib
import importlib.util
import io
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOOM = ROOT / "loom"


class ArchitectureTest(unittest.TestCase):
    def test_modules_only_depend_on_core(self):
        """箭頭只往核心指；核心不 import 任何 loom 模組；同層模組不互相 import；只用標準函式庫。"""
        for path in LOOM.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level:
                    target = node.module or ""
                    if path.stem == "core":
                        self.fail(f"core 不可以 import loom 的其他模組：{target}")
                    if path.stem != "__init__":
                        self.assertEqual(target, "core", f"{path.name} import 了 {target}")
                elif isinstance(node, (ast.Import, ast.ImportFrom)) and not getattr(node, "level", 0):
                    names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module]
                    for n in names:
                        self.assertIsNotNone(importlib.util.find_spec(n.split(".")[0]), n)
                        self.assertNotIn("site-packages", str(importlib.util.find_spec(n.split(".")[0]).origin))


class ExamplesTest(unittest.TestCase):
    def _run(self, name: str) -> str:
        spec = importlib.util.spec_from_file_location(name, ROOT / "examples" / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            if name == "support_agent":
                from loom.runtime import run_virtual
                run_virtual(mod.main())
                mod.evaluate()
            else:
                mod.main()
        return out.getvalue()

    def test_support_agent(self):
        out = self._run("support_agent")
        self.assertIn("run_finished interrupted", out)
        self.assertIn("第二次 resume → ignored；實際退款筆數 1", out)

    def test_coding_agent(self):
        out = self._run("coding_agent")
        self.assertIn("status=unverified", out)
        self.assertIn("實際寫檔次數=1", out)

    def test_research_agent(self):
        out = self._run("research_agent")
        self.assertIn("沒有證據編號", out)
        self.assertIn("resume：status=done", out)


if __name__ == "__main__":
    unittest.main()
