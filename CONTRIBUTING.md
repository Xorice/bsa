# 贡献指南

欢迎改进审计指引、离线渲染器与合成用例。先说明具体问题、期望行为和可复现条件，保持改动围绕一个可审查的问题。

## 内容约定

- 两个 `SKILL.md` 都只保留用途、关键边界和按需索引；将专项、修复、交付细节放到 `references/`，不要让入口要求预读所有资料。
- 每个 skill 的必需资源保留在自己的 `skills/<skill-name>/` 内。伙伴 skill 从宿主清单按名字/安装位置发现，明确共享资料的触发条件与不可用时的降级，不用固定跨 skill 相对链接制造隐式依赖。`bsa-lite` 可复用完整版审计规则，但保持文本交付，不加载报告渲染流程。仓库检查、测试与贡献文档留在根目录。
- 审计默认只读；`bsa-lite` 在用户要求实施修复时推进修改与验证。保留实际隔离要求，不将通用声明写成对每个项目或线上数据操作的自动授权。
- 区分源码事实、模型推演、隔离观测和线上证据，修复建议不表示已有防护。不要将未知上限写成无限收益。
- 每条发现解释有依据的潜在恶意利用与必要前提；缺少最终利用证据时醒目标记待验证，不能省略合理的高影响提醒，也不计作已确认影响。
- 示例和测试使用合成数据。不要提交真实游戏源码、私有审计材料、真实账号、密钥或线上利用脚本；分享问题前检查附件与日志。
- Python 工具保持标准库实现和离线运行。修改输入契约或命令行参数时，同步更新 [流程图约定](skills/blox-security-audit/references/diagrams.md)、[README](README.md) 和相关测试。

## 验证改动

在仓库根目录运行：

```sh
python -B scripts/check_repo.py
python -B -m unittest discover -s tests -v
```

修改渲染布局时，再生成示例并检查浏览器中的文字、连线、摘要和完整关系：

```sh
python -B skills/blox-security-audit/scripts/render_flow.py --input skills/blox-security-audit/examples/flows.json --output out/flows.html --svg-dir out/svg --mermaid-dir out/mermaid
```

为行为变化提供能验证输入约束、输出结果或关键不变量的测试。提交说明包含问题、最终行为和验证结果；若有环境或覆盖限制，一并说明。生成文件、缓存和本地审计产物留在忽略目录中。

## 许可

提交贡献即表示你有权提交这些内容，并同意以本仓库的 [MIT 许可证](LICENSE) 分发该贡献。修改许可文本时同步更新各 skill 内的许可证，以便独立分发。
