
import argparse
import csv
import io
import math
import os
import sys
import tempfile
from pathlib import Path


def read_text(path, encoding):
    data = path.read_bytes()
    if encoding != "auto":
        return data.decode(encoding)
    for candidate in ("utf-8-sig", "gb18030"):
        try:
            return data.decode(candidate)
        except UnicodeDecodeError:
            pass
    raise UnicodeError("无法用 UTF-8 或 GB18030 解码文件")


def valid_name(name):
    return all(part.isalpha() for part in name.split("·"))


def valid_values(row, integer_fields, ranges):
    try:
        for field in integer_fields:
            if row[field]:
                int(row[field])
        for field, low, high in ranges:
            if row[field]:
                value = float(row[field])
                if not math.isfinite(value) or not low <= value <= high:
                    return False
    except (ValueError, TypeError):
        return False
    return True


def write_outputs(outputs):
    staged = []
    try:
        for path, fields, rows in outputs:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", newline="", dir=path.parent,
                prefix=f".{path.name}.", suffix=".tmp", delete=False
            ) as file:
                staged.append(Path(file.name))
                writer = csv.DictWriter(file, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
        for temporary, (path, _, _) in zip(staged, outputs):
            os.replace(temporary, path)
    finally:
        for temporary in staged:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="CSV 数据清洗工具")
    parser.add_argument("--input", required=True, help="输入 CSV 文件")
    parser.add_argument("--output", required=True, help="输出 CSV 文件")
    parser.add_argument(
        "--encoding",
        choices=["auto", "utf-8", "utf-8-sig", "gb18030"],
        default="auto", help="输入文件编码，默认自动检测"
    )
    parser.add_argument("--required", nargs="+", default=[], help="必填字段")
    parser.add_argument("--unique", nargs="+", help="去重字段，默认按整行去重")
    parser.add_argument("--integer", nargs="+", default=[], help="整数字段")
    parser.add_argument(
        "--range", nargs=3, action="append", default=[],
        metavar=("FIELD", "MIN", "MAX"), help="字段数值范围"
    )
    parser.add_argument("--name-field", help="按字母及间隔号校验指定姓名字段")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    rejected_path = output_path.with_name("rejected.csv")

    if input_path.resolve() in (output_path.resolve(), rejected_path.resolve()):
        parser.error("输入文件不能与输出文件或拒绝记录文件相同")
    if output_path.resolve() == rejected_path.resolve():
        parser.error("输出文件不能命名为 rejected.csv")

    ranges = []
    for field, low, high in args.range:
        try:
            low, high = float(low), float(high)
        except ValueError:
            parser.error(f"范围参数不是数字：{field}")
        if not all(map(math.isfinite, (low, high))) or low > high:
            parser.error(f"无效的数值范围：{field}")
        ranges.append((field, low, high))

    try:
        text = read_text(input_path, args.encoding)
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        fields = reader.fieldnames

        if not fields or any(not field.strip() for field in fields):
            raise csv.Error("CSV 表头为空或包含空字段名")
        if len(set(fields)) != len(fields) or "error_reason" in fields:
            raise csv.Error("CSV 表头重复或包含保留字段 error_reason")

        unique_fields = args.unique or fields
        checked = (
            args.required + unique_fields + args.integer
            + [r[0] for r in ranges]
        )
        if args.name_field:
            checked.append(args.name_field)
        for field in checked:
            if field not in fields:
                parser.error(f"字段不存在：{field}")

        kept, rejected = [], []
        total = missing = invalid = duplicates = 0
        seen = set()

        for row in reader:
            total += 1
            if None in row or any(value is None for value in row.values()):
                raise csv.Error(
                    f"第 {reader.line_num} 行字段数量与表头不一致"
                )

            original = row.copy()
            row = {
                key: value.strip()
                for key, value in row.items()
            }

            if any(not row[field] for field in args.required):
                missing += 1
                reason = "必填字段缺失"
            else:
                value_ok = valid_values(row, args.integer, ranges)
                name_invalid = (
                    args.name_field and row[args.name_field]
                    and not valid_name(row[args.name_field])
                )

                if not value_ok or name_invalid:
                    invalid += 1
                    reason = (
                        "数值类型或范围非法"
                        if not value_ok else "姓名格式非法"
                    )
                else:
                    key = tuple(row[field] for field in unique_fields)
                    if key in seen:
                        duplicates += 1
                        reason = "重复记录"
                    else:
                        seen.add(key)
                        reason = None

            if reason:
                rejected.append({
                    **original,
                    "error_reason": reason
                })
            else:
                kept.append(row)

    except (OSError, UnicodeError, csv.Error) as error:
        print(f"输入错误：{error}", file=sys.stderr)
        return 3

    for path in (output_path, rejected_path):
        if path.exists() and not path.is_file():
            print(
                f"输出错误：目标不是普通文件：{path}",
                file=sys.stderr
            )
            return 4

    try:
        write_outputs([
            (output_path, fields, kept),
            (rejected_path, fields + ["error_reason"], rejected),
        ])
    except OSError as error:
        print(f"输出错误：{error}", file=sys.stderr)
        return 4

    print(f"总记录数：{total}")
    print(f"保留记录：{len(kept)}")
    print(f"缺失值拒绝：{missing}")
    print(f"非法值拒绝：{invalid}")
    print(f"重复值拒绝：{duplicates}")

    return 1 if rejected else 0


if __name__ == "__main__":
    sys.exit(main())
