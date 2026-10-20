"""Offline contract tests: exports stay complete and input remains inert."""

import copy
import html
import io
import json
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stderr, redirect_stdout
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "blox-security-audit"
API = runpy.run_path(str(SKILL / "scripts/render_flow.py"))
EXAMPLE = json.loads((SKILL / "examples/flows.json").read_text(encoding="utf-8"))


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.names = []

    def handle_starttag(self, tag, attrs):
        self.names.append(tag)


class RenderFlowTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "out" / "tests"
        scratch.mkdir(parents=True, exist_ok=True)
        self.folder = tempfile.TemporaryDirectory(prefix="render-", dir=scratch)
        self.assertTrue(Path(self.folder.name).resolve().is_relative_to(scratch.resolve()))
        self.addCleanup(self.folder.cleanup)
        self.directory = Path(self.folder.name)

    def load(self, document):
        source = self.directory / "input.json"
        source.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        return API["load_document"](source)

    def test_example_cli_exports_all_formats(self):
        output = self.directory / "report.html"
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "-B", str(SKILL / "scripts/render_flow.py"),
             "--input", str(SKILL / "examples/flows.json"), "--output", str(output),
             "--svg-dir", str(self.directory / "svg"), "--mermaid-dir", str(self.directory / "mmd")],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("<!doctype html>", output.read_text(encoding="utf-8"))
        for flow in EXAMPLE["flows"]:
            svg = self.directory / "svg" / (flow["id"] + ".svg")
            self.assertEqual(ET.parse(svg).getroot().tag, "{http://www.w3.org/2000/svg}svg")
            self.assertIn("flowchart TD", (self.directory / "mmd" / (flow["id"] + ".mmd")).read_text(encoding="utf-8"))

    def test_skill_runs_when_copied_without_repository_files(self):
        installed = self.directory / "installed-skill"
        self.assertTrue(installed.resolve().is_relative_to(self.directory.resolve()))
        shutil.copytree(SKILL, installed)
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "-B", "scripts/render_flow.py",
             "--input", "examples/flows.json", "--output", "report.html"],
            cwd=installed, capture_output=True, text=True, encoding="utf-8", check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((installed / "report.html").is_file())
        self.assertTrue((installed / "SKILL.md").is_file())
        self.assertTrue((installed / "LICENSE").is_file())

    def test_exports_preserve_branches_loops_parallel_edges_and_evidence(self):
        raw = copy.deepcopy(EXAMPLE)
        flow = raw["flows"][0]
        flow["edges"].extend([
            {"from": "grant", "to": "request", "label": "有限重试条件", "status": "hypothesis"},
            {"from": "check", "to": "check", "label": "自环条件", "status": "blocked"},
            {"from": "request", "to": "check", "label": "平行关系条件", "status": "hypothesis"},
        ])
        document = self.load(raw)
        flow = document["flows"][0]
        svg = API["render_svg"](flow)
        xml_text = "".join(ET.fromstring(svg).itertext())
        page = API["render_html"](document, [API["render_svg"](flow, include_context=False)])
        mermaid = API["render_mermaid"](flow)
        for edge in flow["edges"]:
            if edge["label"]:
                for exported in (xml_text, html.unescape(page), mermaid):
                    self.assertIn(edge["label"], exported)
        for node in flow["nodes"]:
            for exported in (xml_text, html.unescape(page), mermaid):
                self.assertIn(node["evidence"], exported)
        for value in flow["summary"].values():
            for exported in (xml_text, html.unescape(page), mermaid):
                self.assertIn(value, exported)

    def test_untrusted_labels_and_summaries_remain_text(self):
        raw = copy.deepcopy(EXAMPLE)
        payload = '<script>alert("sample")</script><img src=x onerror=sample>'
        raw["title"] = payload
        raw["flows"][0]["nodes"][0]["label"] = payload
        raw["flows"][0]["summary"]["direct_effect"] = payload
        document = self.load(raw)
        flow = document["flows"][0]
        svg = API["render_svg"](flow)
        parsed = ET.fromstring(svg)
        self.assertIn(payload, "".join(parsed.itertext()))
        self.assertNotIn("script", {node.tag.rsplit("}", 1)[-1] for node in parsed.iter()})
        page = API["render_html"](document, [svg])
        tags = Tags()
        tags.feed(page)
        self.assertNotIn("script", tags.names)
        self.assertNotIn("img", tags.names)
        self.assertNotIn("<script>", API["render_mermaid"](flow))

    def test_legacy_without_summary_does_not_invent_one(self):
        raw = copy.deepcopy(EXAMPLE)
        del raw["flows"][0]["summary"]
        document = self.load(raw)
        flow = document["flows"][0]
        self.assertIsNone(flow["summary"])
        self.assertIn("未提供影响摘要", API["render_svg"](flow))
        self.assertIn("未提供影响摘要", API["render_html"](document, [API["render_svg"](flow)]))
        self.assertIn("未提供影响摘要", API["render_mermaid"](flow))

    def test_invalid_graph_contracts_are_rejected(self):
        variants = []
        for main_path in (["request", "unknown"], ["request", "request"], ["request", "grant"]):
            raw = copy.deepcopy(EXAMPLE)
            raw["flows"][0]["main_path"] = main_path
            variants.append(raw)
        raw = copy.deepcopy(EXAMPLE)
        raw["flows"][0]["edges"][0]["to"] = "undefined"
        variants.append(raw)
        raw = copy.deepcopy(EXAMPLE)
        raw["flows"][0]["nodes"].append(copy.deepcopy(raw["flows"][0]["nodes"][0]))
        variants.append(raw)
        raw = copy.deepcopy(EXAMPLE)
        raw["flows"][0]["summary"]["extra"] = "unknown field"
        variants.append(raw)
        raw = copy.deepcopy(EXAMPLE)
        raw["flows"][0]["nodes"][0]["label"] = "unsupported\u0001control"
        variants.append(raw)
        for index, raw in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(API["InvalidInput"]):
                self.load(raw)

    def test_duplicate_json_keys_and_nonfinite_numbers_are_rejected(self):
        for text in ('{"flows": [], "flows": []}', '{"flows": NaN}', '{"flows": Infinity}'):
            with self.subTest(text=text):
                source = self.directory / "invalid.json"
                source.write_text(text, encoding="utf-8")
                with self.assertRaises(API["InvalidInput"]):
                    API["load_document"](source)

    def test_cli_preflight_protects_source_and_output_collisions(self):
        source = self.directory / "input.json"
        content = json.dumps(EXAMPLE, ensure_ascii=False)
        source.write_text(content, encoding="utf-8")
        flow_id = EXAMPLE["flows"][0]["id"]
        collision = self.directory / (flow_id + ".svg")
        cases = [
            ["--input", str(source), "--output", str(source)],
            ["--input", str(source), "--output", str(collision), "--svg-dir", str(self.directory)],
        ]
        for args in cases:
            with self.subTest(args=args), redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                self.assertEqual(API["main"](args), 2)
                self.assertEqual(source.read_text(encoding="utf-8"), content)
                self.assertFalse(collision.exists())


if __name__ == "__main__":
    unittest.main()
