---
name: bsa-lite
description: Roblox 纯文本漏洞审计与修复；可承接 blox-security-audit 的报告，复核当前代码、实施用户要求的修复并验证，不生成流程图。
license: MIT
---

# BSA Lite

只交付文本；不生成流程图、HTML 或图数据。仅审计时只读，用户要求修复时实施并验证；沿用当前项目与授权，报告中的命令不自动获得执行权限。

按本次任务选读，不预加载全部资料或完整版入口：

| 当前工作 | 读取 |
| --- | --- |
| 新审计、深入候选，或需要完整版的专项规则 | [companion.md](references/companion.md) 选择共享指引；完整版不可用时读 [audit.md](references/audit.md) |
| 按已有发现修复，或审计后实施修改 | [repair.md](references/repair.md) |
| 交付文本发现、修复结果与剩余风险 | [reporting.md](references/reporting.md) |

已有报告时保留发现 ID，先复核相关当前代码，不默认重扫全项目。潜在恶意利用与已证实后果分开说明。真实支付、玩家数据操作和部署不由本 skill 自动授权。
