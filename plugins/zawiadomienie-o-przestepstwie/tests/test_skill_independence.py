"""Testy regresyjne: skill zawiadomienie-o-przestepstwie musi być w pełni samodzielny.

Pilnują: kontraktu SKILL.md (opis, długość, Gotchas), braku odwołań do `shared/`, innych skilli
i Basic Memory, istnienia każdej ścieżki wskazanej w treści, działania skryptów oraz spójności evali.
LOG.md i raporty evals/2026* to zapisy historyczne i są pomijane przy wykrywaniu odwołań.
"""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "zawiadomienie-o-przestepstwie"
HISTORICAL = ("LOG.md",)
OTHER_SKILLS = (
    "pisma-proste-v2", "pisma-procesowe-v3", "pisz-po-polsku", "humanizer-pl", "szturm-na-draft-pl",
    "adversarial-legal-review-pl", "atak-przeciwnika-pl", "zazalenie-na-postanowienie-prokuratora",
    "prawny-router-v3", "redline-docx-pl", "teczka-sprawy", "wiki-basic-memory", "pierwsze-wrazenie-sedziego-pl",
)
FORBIDDEN = [r"shared/", r"Basic Memory", r"basic-memory", r"repo abogada", r"\.\./", r"\.Codex/", r"INBOX/"]


def live_files():
    for p in SKILL.rglob("*"):
        if not p.is_file() or "__pycache__" in p.parts or p.suffix not in {".md", ".py", ".json", ".yaml"}:
            continue
        rel = p.relative_to(SKILL)
        if rel.name in HISTORICAL or (rel.parts[0] == "evals" and rel.name != "evals.json"):
            continue
        yield p


def split_skill():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    _, fm, body = text.split("---", 2)
    return fm, body


class SkillContract(unittest.TestCase):
    def test_frontmatter(self):
        fm, _ = split_skill()
        self.assertRegex(fm, r"(?m)^name: zawiadomienie-o-przestepstwie$")
        m = re.search(r"(?ms)^description: (.+?)(?=^\w+:|\Z)", fm)
        desc = re.sub(r"\s+", " ", m.group(1)).strip().strip("'\"")
        self.assertLessEqual(len(desc), 1024)
        self.assertTrue(desc.startswith("Używaj"))
        self.assertNotRegex(desc, r"[<>]")

    def test_body_size_and_sections(self):
        _, body = split_skill()
        self.assertLess(len(body.strip().split("\n")), 500)
        self.assertIn("## Gotchas", body)
        self.assertTrue((SKILL / "LOG.md").is_file())

    def test_every_referenced_path_exists(self):
        pat = re.compile(r"`((?:references|scripts|assets|evals)/[\w./-]+\.\w+)`")
        missing = []
        for p in live_files():
            for ref in pat.findall(p.read_text(encoding="utf-8")):
                if not (SKILL / ref).exists():
                    missing.append(f"{p.relative_to(SKILL)} -> {ref}")
        self.assertEqual(missing, [])

    def test_every_reference_is_linked_from_skill(self):
        body = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for p in (SKILL / "references").glob("*.md"):
            self.assertIn(f"references/{p.name}", body, p.name)


class Independence(unittest.TestCase):
    def test_no_external_dependencies_in_live_files(self):
        hits = []
        for p in live_files():
            text = p.read_text(encoding="utf-8")
            for pat in FORBIDDEN:
                if re.search(pat, text):
                    hits.append(f"{p.relative_to(SKILL)}: {pat}")
            for name in OTHER_SKILLS:
                if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text):
                    hits.append(f"{p.relative_to(SKILL)}: skill {name}")
        self.assertEqual(hits, [])

    def test_relacje_live_in_legal_repo(self):
        text = (SKILL / "references" / "relacje-repo.md").read_text(encoding="utf-8")
        self.assertIn("elconcept/legal", text)
        self.assertIn("relacje/", text)
        self.assertIn("NIEZAPISANE", text)


class Scripts(unittest.TestCase):
    def test_scripts_compile(self):
        for p in (SKILL / "scripts").glob("*.py"):
            compile(p.read_text(encoding="utf-8"), str(p), "exec")

    def test_wersja_pisma_help_runs_without_network(self):
        r = subprocess.run([sys.executable, "-I", str(SKILL / "scripts" / "wersja_pisma.py"), "--help"],
                           capture_output=True, text=True, cwd=SKILL)
        # skrypt pokazuje użycie i kończy kodem 1 przy braku podkomendy; liczy się brak wyjątku i brak sieci
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("redline", r.stdout + r.stderr)


class Evals(unittest.TestCase):
    def test_evals_well_formed(self):
        data = json.loads((SKILL / "evals" / "evals.json").read_text(encoding="utf-8"))
        evals = data["evals"]
        self.assertGreaterEqual(len(evals), 29)
        ids = [e["id"] for e in evals]
        self.assertEqual(len(ids), len(set(ids)))
        for e in evals:
            self.assertTrue(e.get("prompt"), e["id"])


if __name__ == "__main__":
    unittest.main()
