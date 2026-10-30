# CSV 命令行数据清洗工具

使用 Python 标准库实现的轻量级 CSV 数据清洗程序，支持编码处理、缺失值过滤、重复记录去除和非法值校验。

程序通过命令行参数指定输入文件、输出文件及清洗规则，不依赖固定列名，可处理不同结构的 CSV 数据。

## 1. 运行环境

- 操作系统：Windows
- Python：3.11.18
- 开发工具：PyCharm
- 版本管理：Git
- 第三方依赖：无

程序仅使用 Python 标准库，无需额外安装依赖。

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

主要文件说明：

- `clean.py`：命令行数据清洗程序
- `examples/input.csv`：三列综合清洗样例
- `examples/input_bom.csv`：UTF-8 BOM 编码样例
- `examples/input_gb.csv`：GB18030 编码样例
- `examples/products.csv`：六列商品数据样例
- `tests/test_clean.py`：自动化测试
- `test_results.log`：测试运行记录

`output.csv` 和 `rejected.csv` 由程序运行时生成，不作为必要的源代码文件提交。

## 3. 核心功能

### 3.1 编码处理

支持 UTF-8、UTF-8 BOM 和 GB18030 编码。

默认使用自动模式，优先尝试 UTF-8（兼容 BOM），解码失败后尝试 GB18030，也可通过 `--encoding` 手动指定。

输出文件统一采用 UTF-8 编码。

### 3.2 缺失值处理

使用 `--required` 指定一个或多个必填字段。

程序清除字段首尾空白，若任意必填字段为空，则拒绝该记录。

未设置为必填的字段允许为空，不自动推测或填补缺失值。

### 3.3 重复值处理

默认按整行内容去重，也可使用 `--unique` 指定一个或多个去重字段。

保留第一次出现的有效记录，并保持原有顺序。

缺失或非法记录不会占用去重键。

### 3.4 非法值校验

支持以下规则：

- `--integer`：检查指定字段是否为整数
- `--range`：检查指定字段是否满足数值范围
- `--name-field`：检查指定姓名字段格式

数值校验拒绝不符合规则的类型、越界数值以及 NaN、Infinity 等非有限数值。

姓名校验允许 Unicode 字母及间隔号 `·`。该规则仅作为实验中的可选校验约束，并不代表所有真实姓名的通用标准。

未配置的字段不执行额外业务校验。

### 3.5 拒绝记录

程序将有效记录写入指定输出文件，并在同一目录生成 `rejected.csv`。

拒绝文件保留原始字段，并新增 `error_reason` 列说明拒绝原因。

清洗顺序为：

1. 必填字段检查
2. 非法值校验
3. 重复值检查

每条被拒绝的记录只计入一个主要拒绝类别。

## 4. 命令行使用

在项目根目录运行：

```bash
python clean.py --input examples/input.csv --output examples/output.csv --required name age --unique id --integer age --range age 0 120 --name-field name
```

命令行参数：

| 参数 | 作用 |
|---|---|
| `--input` | 输入 CSV 文件路径，必填 |
| `--output` | 输出 CSV 文件路径，必填 |
| `--encoding` | 输入编码，默认 auto |
| `--required` | 指定必填字段 |
| `--unique` | 指定去重字段，默认整行去重 |
| `--integer` | 指定整数字段 |
| `--range` | 指定字段数值范围，可重复使用 |
| `--name-field` | 指定需要进行姓名校验的字段 |
| `--help` | 显示命令行帮助 |

通过参数配置清洗规则，能够在不修改源码的情况下处理不同字段结构的数据。

## 5. 输入输出样例

### 5.1 三列综合清洗测试

输入文件：`examples/input.csv`

包含 19 条记录，覆盖正常数据、必填字段缺失、重复主键、数值越界、非法整数和非法姓名。

运行命令：

```bash
python clean.py --input examples/input.csv --output examples/output.csv --required name age --unique id --integer age --range age 0 120 --name-field name
```

预期统计：

| 统计项 | 数量 |
|---|---:|
| 总记录数 | 19 |
| 保留记录 | 7 |
| 缺失值拒绝 | 2 |
| 非法值拒绝 | 8 |
| 重复值拒绝 | 2 |

有效输出为：

```csv
id,name,age
1,张三,20
3,王五,22
5,赵六,21
2,李四,25
9,小丽,25
12,王·小明,0
13,Alice,120
```

其余 12 条记录保存至 `rejected.csv`，包含具体拒绝原因。

### 5.2 多字段兼容性测试

输入文件：`examples/products.csv`

使用六列商品数据：

`sku,product,price,quantity,category,status`

运行命令：

```bash
python clean.py --input examples/products.csv --output examples/out_products.csv --required sku product price quantity --unique sku --integer quantity --range price 0 1000 --range quantity 0 500
```

预期统计：

| 统计项 | 数量 |
|---|---:|
| 总记录数 | 12 |
| 保留记录 | 6 |
| 缺失值拒绝 | 1 |
| 非法值拒绝 | 4 |
| 重复值拒绝 | 1 |

该测试验证了动态字段读取、多字段规则配置、非法记录不占用去重键以及未配置字段保留原值等行为。

例如，`P003` 的第一条记录价格非法，被拒绝；后续同一商品编号的合法记录仍可保留。

`status=unknown` 的记录也会保留，因为当前程序未配置状态枚举校验规则。

## 6. 异常处理与退出码

程序通过退出码区分处理结果：

| 退出码 | 含义 |
|---|---|
| 0 | 处理成功，无拒绝记录 |
| 1 | 处理完成，存在拒绝记录 |
| 2 | 命令行参数或规则错误 |
| 3 | 输入文件、解码或 CSV 格式错误 |
| 4 | 输出文件写入失败 |

对预期错误输出明确的提示信息。

输入文件在完成读取和格式检查后才进入输出阶段，避免输入处理失败时覆盖已有结果。

输出使用临时文件写入，完成后替换目标文件，降低中途写入失败造成文件不完整的风险。

## 7. 自动化测试

使用 Python 标准库 `unittest`，通过 `subprocess` 调用实际清洗程序，并使用临时目录隔离测试文件。

测试覆盖以下 12 个场景：

1. 综合清洗及拒绝原因统计
2. UTF-8、UTF-8 BOM、GB18030 编码
3. 全部数据合法
4. 非法记录不占用去重键
5. 不存在的字段配置
6. 输入文件不存在
7. CSV 行结构及引号异常
8. 编码解码失败
9. 输出目录不存在
10. 输入输出路径冲突
11. 空文件与仅有表头的文件
12. 六列商品数据兼容性

运行全部测试：

```bash
python -m unittest discover -s tests -v
```

保存测试日志：

```bash
python -m unittest discover -s tests -v > test_results.log 2>&1
```

测试结果及执行时间以 `test_results.log` 中的实际运行记录为准。

## 8. 设计说明与局限性

本项目优先保证正确性、可读性和边界处理，采用 Python 标准库实现，不引入不必要的第三方依赖或复杂框架。

主要设计包括：

- 根据 CSV 表头动态读取和输出字段
- 使用命令行参数配置清洗规则
- 使用集合提高重复值检查效率
- 先检查有效性，再登记去重键
- 保留拒绝记录及具体原因
- 使用临时输出文件减少异常写入风险

当前版本存在以下限制：

- 自动编码判断基于候选编码尝试，不能保证准确识别所有字符编码。
- 两个输出文件分别替换，不能保证同时更新的原子性。
- 输入数据一次性读入内存，更适合小型 CSV 文件。
- 非必填数值字段为空时允许保留，不自动填补。
- 不自动识别字段业务含义，日期、邮箱、枚举等规则需要额外实现。
- 姓名校验采用简化的字符规则，可能不适用于所有真实姓名。

## 9. 复现与版本管理

项目通过 Git 进行版本管理。

首次实现提交：

`4a36771` — `Implement CSV cleaning and boundary tests`

后续增加多字段兼容性测试，相关修改可通过 Git 提交历史查看。

查看当前版本：

```bash
git log -1 --oneline
git rev-parse HEAD
```

复现步骤：

1. 获取项目源码。
2. 使用 Python 3.11 或兼容的 Python 3 环境。
3. 在项目根目录执行 `python -m unittest discover -s tests -v`。
4. 使用第 5 节的命令运行两个清洗样例。
5. 对照预期统计、输出文件和测试日志检查结果。

项目源码：

https://github.com/lemon900/csv-cleaner