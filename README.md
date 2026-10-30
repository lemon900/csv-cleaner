# CSV 命令行数据清洗工具

使用 Python 标准库实现的轻量级 CSV 清洗程序，支持编码读取、缺失值检查、重复记录去除、非法值校验和拒绝记录保存。通过命令行配置规则，不依赖固定列名。

## 1. 运行环境

- 操作系统：Windows
- 开发环境：PyCharm
- Python：3.11.18（实验环境）
- 第三方依赖：无

## 2. 项目结构

```text
csv_cleaner/
├── clean.py
├── README.md
├── .gitignore
├── test_results.log
├── examples/
│   ├── input.csv
│   ├── input_bom.csv
│   ├── input_gb.csv
│   └── products.csv
└── tests/
    └── test_clean.py
```

`output.csv` 和 `rejected.csv` 由程序运行时生成，不需要提交。`test_results.log` 应保存本机真实测试输出。

## 3. 清洗规则

- **编码**：自动模式优先尝试 UTF-8（包括 UTF-8 BOM），失败后尝试 GB18030；也可用 `--encoding` 指定。输出统一使用 UTF-8。
- **缺失值**：对每个字段去除首尾空白；`--required` 指定的字段为空时拒绝该行。
- **重复值**：`--unique` 指定去重字段，可为多个字段；省略时按整行去重，保留第一次出现的有效记录。
- **非法值**：`--integer` 检查整数，`--range FIELD MIN MAX` 检查数值范围，`--name-field` 检查姓名字段。非有限数值（NaN、Infinity）无法通过范围校验。
- **姓名规则**：允许连续的 Unicode 字母，或由单个间隔号 `·` 分隔的字母段；单独的间隔号、连续间隔号、首尾间隔号及数字不通过。该规则仅为实验示例，不是通用姓名标准。

清洗顺序：**必填检查 → 非法值检查 → 去重检查**。只有通过前两项检查的记录才占用去重键。未指定规则的字段不会自动进行业务校验；非必填字段为空时可保留。

有效数据写入 `--output` 指定的文件；拒绝数据写入同目录的 `rejected.csv`，增加 `error_reason` 列并保留原始字段值。

## 4. 运行方法

查看参数：

```bash
python clean.py --help
```

三列姓名年龄数据：

```bash
python clean.py --input examples/input.csv --output examples/output.csv --required name age --unique id --integer age --range age 0 120 --name-field name
```

预期：总记录 19、保留 7、缺失拒绝 2、非法拒绝 8、重复拒绝 2。

六列商品数据：

```bash
python clean.py --input examples/products.csv --output examples/out_products.csv --required sku product price quantity --unique sku --integer quantity --range price 0 1000 --range quantity 0 500
```

预期：总记录 12、保留 6、缺失拒绝 1、非法拒绝 4、重复拒绝 1。`status=unknown` 会被保留，因为没有设置状态枚举规则；无效的首次 `P003` 不会阻止后续合法 `P003` 被保留。

主要命令行选项：

| 选项 | 说明 |
|---|---|
| `--input` / `--output` | 输入、输出 CSV 路径（必填） |
| `--encoding` | `auto`（默认）、`utf-8`、`utf-8-sig`、`gb18030` |
| `--required` | 一个或多个必填字段 |
| `--unique` | 一个或多个去重字段，默认整行 |
| `--integer` | 一个或多个整数字段 |
| `--range` | 数值范围，可重复传入，例如 `--range age 0 120` |
| `--name-field` | 指定需要执行姓名规则的列 |

## 5. 错误处理与退出码

| 退出码 | 含义 |
|---|---|
| 0 | 处理成功，无拒绝记录 |
| 1 | 处理完成，有拒绝记录 |
| 2 | 参数或清洗规则错误 |
| 3 | 输入文件、解码或 CSV 格式错误 |
| 4 | 输出文件写入错误 |

程序先完整读取并检查输入，再写出结果。输出使用同目录临时文件，写入完成后替换目标文件。若目标输出路径已经存在且不是普通文件，会在写出前返回退出码 4，避免覆盖已有有效输出。

## 6. 自动化测试

使用 Python 标准库 `unittest`，通过 `subprocess` 运行真实的 `clean.py`，借助临时目录隔离输出。包含 **15 项测试**：

1. 综合清洗与拒绝原因统计
2. UTF-8、UTF-8 BOM、GB18030 编码
3. 全部记录合法
4. 非法行不占用去重键
5. 不存在的字段配置
6. 输入文件不存在时保护旧输出
7. CSV 列数与引号异常时保护旧输出
8. 编码解码失败
9. 输出目录不存在
10. 输入输出路径冲突
11. 空文件与仅有表头
12. 六列商品数据兼容性
13. 非法姓名间隔号
14. `rejected.csv` 已为目录时保护旧输出
15. CSV 引号、逗号、换行符与重复运行一致性

执行测试：

```bash
python -m unittest discover -s tests -v
```

保存真实测试日志：

```bash
python -m unittest discover -s tests -v > test_results.log 2>&1
```

检查日志末尾的 `Ran 15 tests` 和 `OK`。实际耗时取决于机器与环境。

## 7. 设计取舍与局限

- 代码只依赖标准库，避免复杂配置系统和额外依赖。
- 自动编码识别采用候选解码方式，不能保证区分所有编码。
- 输入一次读入内存，适用于小规模数据，不针对超大型 CSV 优化。
- 两个结果文件分别执行 `os.replace`，**不保证两个文件作为一个事务同时更新**；输出路径预检查只能降低常见风险。
- 非必填的数值字段可为空；整数校验沿用 Python 的 `int()` 格式约定。
- 不自动推断日期、邮箱或枚举等业务约束。

## 8. 复现与版本

在项目根目录运行上文的测试及样例命令，通过 `git log -1 --oneline` 和 `git rev-parse HEAD` 查看实际提交版本。第一次核心实现提交为 `4a36771`，后续改进以 Git 历史为准。

项目仓库：https://github.com/lemon900/csv-cleaner