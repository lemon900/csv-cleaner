import csv
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "clean.py"
RULES = [
    "--required", "name", "age", "--unique", "id",
    "--integer", "age", "--range", "age", "0", "120",
    "--name-field", "name",
]


class CleanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source = self.folder / "input.csv"
        self.output = self.folder / "output.csv"
        self.rejected = self.folder / "rejected.csv"

    def run_clean(self, *options, source=None, output=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--input", str(source or self.source),
             "--output", str(output or self.output), *options],
            capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            check=False,
        )

    def rows(self, path):
        with path.open(encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))

    def test_full_clean(self):
        self.source.write_bytes((ROOT / "examples" / "input.csv").read_bytes())
        result = self.run_clean(*RULES)
        self.assertEqual(result.returncode, 1, result.stderr)
        kept = self.rows(self.output)
        rejected = self.rows(self.rejected)
        self.assertEqual([r["id"] for r in kept], ["1", "3", "5", "2", "9", "12", "13"])
        self.assertEqual(len(rejected), 12)
        self.assertEqual(Counter(r["error_reason"] for r in rejected), {
            "必填字段缺失": 2, "重复记录": 2,
            "数值类型或范围非法": 5, "姓名格式非法": 3,
        })
        self.assertIn("总记录数：19", result.stdout)

    def test_three_encodings(self):
        content = "id,name,age\n1,张三,20\n2,李四,\n"
        for encoding in ("utf-8", "utf-8-sig", "gb18030"):
            with self.subTest(encoding=encoding):
                self.source.write_bytes(content.encode(encoding))
                result = self.run_clean(*RULES)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(len(self.rows(self.output)), 1)
                self.assertEqual(len(self.rows(self.rejected)), 1)
                self.assertEqual(self.rows(self.output)[0]["name"], "张三")

    def test_all_valid(self):
        self.source.write_text("id,name,age\n1,张三,0\n2,Alice,120\n", encoding="utf-8")
        result = self.run_clean(*RULES)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.rows(self.output)), 2)
        self.assertEqual(self.rows(self.rejected), [])

    def test_invalid_row_does_not_block_valid_duplicate_key(self):
        self.source.write_text(
            "id,name,age\n1,张三,abc\n1,张三,20\n1,张三,20\n", encoding="utf-8"
        )
        result = self.run_clean(*RULES)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(self.rows(self.output)), 1)
        self.assertEqual([r["error_reason"] for r in self.rows(self.rejected)], [
            "数值类型或范围非法", "重复记录"
        ])

    def test_unknown_field_returns_2(self):
        self.source.write_text("id,name,age\n1,张三,20\n", encoding="utf-8")
        result = self.run_clean("--required", "salary")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.output.exists())

    def test_missing_input_returns_3_and_preserves_output(self):
        self.output.write_text("previous result", encoding="utf-8")
        result = self.run_clean()
        self.assertEqual(result.returncode, 3)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "previous result")

    def test_invalid_csv_returns_3_and_preserves_output(self):
        examples = (
            "id,name,age\n1,张三\n",
            "id,name,age\n1,张三,20,extra\n",
            'id,name,age\n1,"张三,20\n',
        )
        for content in examples:
            with self.subTest(content=content):
                self.source.write_text(content, encoding="utf-8")
                self.output.write_text("previous result", encoding="utf-8")
                result = self.run_clean()
                self.assertEqual(result.returncode, 3, result.stderr)
                self.assertEqual(self.output.read_text(encoding="utf-8"), "previous result")

    def test_invalid_encoding_returns_3(self):
        self.source.write_bytes(b"id,name,age\n1,\x81,20\n")
        result = self.run_clean()
        self.assertEqual(result.returncode, 3, result.stderr)

    def test_bad_output_directory_returns_4(self):
        self.source.write_text("id,name,age\n1,张三,20\n", encoding="utf-8")
        result = self.run_clean(output=self.folder / "missing" / "output.csv")
        self.assertEqual(result.returncode, 4, result.stderr)

    def test_path_collision_returns_2(self):
        self.source.write_text("id,name,age\n1,张三,20\n", encoding="utf-8")
        result = self.run_clean(output=self.source)
        self.assertEqual(result.returncode, 2)

    def test_empty_file_and_header_only(self):
        self.source.write_text("", encoding="utf-8")
        self.assertEqual(self.run_clean().returncode, 3)