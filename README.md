# Blox Security Audit

面向自有或获授权 Roblox 项目的防御性源码审计 skill。帮助 agent 追踪入口、服务端约束、第三方依赖、持久化与跨系统失败路径，输出可复核的代码证据、影响边界、修复建议和漏洞流程图。未发现问题时，说明已检查范围、有效防护和剩余盲区。

仓库采用 [REA](https://github.com/morluto/rea/tree/main) 的 `skills/<name>/` 布局，skill 入口为 [skills/blox-security-audit/SKILL.md](skills/blox-security-audit/SKILL.md)。审计依靠宿主提供的文件读取、搜索、Studio 和可选委派能力；不绑定特定 agent、MCP、框架或付费服务。

## 目录

```text
blox-security-audit/
├── skills/
│   └── blox-security-audit/   # 可独立复制安装的 skill 目录
│       ├── SKILL.md             # 审计入口与按需加载索引
│       ├── agents/openai.yaml   # 支持该格式的宿主可读取的界面元数据
│       ├── references/          # 定位、推理、验证、报告与流程图约定
│       ├── scripts/render_flow.py # 离线生成 HTML、SVG 和 Mermaid 源码
│       ├── examples/flows.json  # 合成示例，不含真实项目源码或审计报告
│       └── LICENSE              # 独立分发时保留的 MIT 许可证
├── scripts/check_repo.py        # 检查仓库结构、元数据与本地 Markdown 链接
├── tests/test_render_flow.py    # Python unittest 测试
├── .github/workflows/validate.yml
├── .editorconfig               # UTF-8、LF 与缩进约定
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

## 在 agent 中使用

将仓库内的 `skills/blox-security-audit/` 目录复制到宿主约定的 skill 目录，或按宿主文档将发现路径指向该目录。例如，目标为 `<宿主的 skills 目录>/blox-security-audit/SKILL.md`。保留该目录中的 `SKILL.md`、`agents/`、`references/`、`scripts/`、`examples/` 和 `LICENSE`，维持相对位置；运行资源均包含在该目录内。具体配置和加载方式由宿主决定，复制文件本身不保证自动安装或启用。

支持 skill 调用的宿主可使用其调用语法，例如 `$blox-security-audit`。其他 agent 可先读取安装目录中的 `SKILL.md`，再按其中索引读取相关参考文件；直接使用本仓库时读取 `skills/blox-security-audit/SKILL.md`。skill 内的 `agents/openai.yaml` 是可选的宿主界面元数据。

可向 agent 提供这样的任务：

```text
读取 skills/blox-security-audit/SKILL.md，对当前已授权的 Roblox 项目做源码审计。
默认只读，重点检查交互入口、材料与奖励结算、第三方依赖和持久化恢复。
输出有证据的发现、影响上限、修复建议及覆盖盲区；发现问题时生成流程图。
```

上例从仓库根目录使用；安装后将入口路径替换为实际安装路径。提供目标目录、版本和已有授权范围即可；按实际任务补充可运行环境与允许动作。缺少 Studio 或委派能力时，agent 可以继续本地串行分析。

## 默认权限与隔离

默认只读源工程，允许在约定目录写本地审计产物。验证优先采用纯函数、固定样本和内存适配器；是否隔离取决于真实依赖与外部服务连接。Studio 模式、mock 标志或“测试”名称本身不能证明隔离。

本 skill 不自动授权修改玩法、生产服务调用、真实账户或资产操作、存档写入及压力测试。已有明确授权可沿用；新增运行动作需要遵循本次项目范围与 [验证约定](skills/blox-security-audit/references/validation.md)。

## 从示例生成流程图

工具使用 Python 3 标准库，无需安装 Python 包、Node 或 Mermaid。建议 Python 3.10 或更新版本。以下命令在仓库根目录执行；按环境将 `python` 改为 `python3` 或 `py -3`。

```sh
python -B skills/blox-security-audit/scripts/render_flow.py --input skills/blox-security-audit/examples/flows.json --output out/flows.html --svg-dir out/svg --mermaid-dir out/mermaid
```

打开 `out/flows.html` 查看自包含 HTML；`out/svg/` 保存每张图的独立 SVG，`out/mermaid/` 保存供下游渲染的 `.mmd` 文本。生成过程不访问网络，HTML 不依赖 JavaScript、CDN 或远程字体。指定输出文件会被覆盖，请使用本次任务的产物目录。

默认正文 14px、主标题 22px、后果摘要 18px，图内正文 16px；画布最大宽度 1200px，宽屏不会继续放大图中文字。完整路径条件与证据可以展开查看。

示例仅演示合成的业务逻辑与证据表达，不代表任何真实游戏存在漏洞。实际审计时自行编写 JSON；四项摘要应说明直接后果、可利用程度、成立条件和证据边界。完整格式与路径状态见 [流程图约定](skills/blox-security-audit/references/diagrams.md)。渲染器只校验输入结构并绘图，不分析源码，也不判断证据真假。

本地审计产物可放在 `audit/`；`out/`、`dist/` 和 `audit/` 已加入 Git 忽略规则。忽略规则不会移除已经跟踪或泄露的文件。

## 本地检查

```sh
python -B scripts/check_repo.py
python -B -m unittest discover -s tests -v
```

仓库检查验证结构、本地 Markdown 链接、必要 frontmatter、Python 语法、示例输入及缓存文件，并要求 skill 文档不依赖安装目录之外的文件；不替代完整 YAML 解析或审计能力评估。测试覆盖三种导出、分支与回路保留、文本转义、旧格式兼容、覆盖输入文件的保护，以及单独复制 skill 目录后的运行。测试临时文件放在 `out/tests/` 下并在结束时清理。

GitHub Actions 在 push 和 pull request 时运行相同命令，无需安装第三方依赖。工作流固定了官方 [checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1) 和 [setup-python v7.0.0](https://github.com/actions/setup-python/releases/tag/v7.0.0) 的提交版本；更新时核对发布记录与 SHA。

## 局限、贡献与许可

审计结论只适用于已读到的版本、配置与覆盖范围。源码缺失、关键依赖不可见或运行条件未验证时，应明确标注缺口；不能将“未发现”作为安全保证。静态推导、模型结果、隔离运行和线上证据须区分记录，详见 [报告约定](skills/blox-security-audit/references/reporting.md)。

覆盖按入口/效果及相关生命周期记录；对关键防护继续追踪成功和失败分支的实际副作用。候选使用统一的缺陷、待验证风险与加固分类；有历史报告时逐项说明仍成立、修复、反证或未完成的证据。重复运行的结果仍可能不同，这些记录用于解释差异，不保证穷尽所有漏洞。

贡献前阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。提交可复现的合成用例，避免提交真实游戏源码、私有漏洞报告、账号、密钥或线上利用脚本。

仓库使用 [MIT 许可证](LICENSE)；skill 目录内包含同一份 [许可证](skills/blox-security-audit/LICENSE)，复制安装或独立分发时一并保留。
