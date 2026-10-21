---
name: blox-security-audit
description: 审计自有或获授权 Roblox 项目的漏洞与逻辑缺陷，检查本地或 Studio 源码与依赖，交付证据、覆盖依据及流程图。纯文本与修复任务可由 bsa-lite 承接。
license: MIT
---

# Blox Security Audit

完整版审计：从实际源码交付证据、影响、修复建议与流程图。默认只读业务源码，可写本地审计产物；沿用当前项目与授权，不自动执行真实业务或改动玩家数据。

按阶段和机制选读，不预加载全部资料：

| 当前工作 | 读取 |
| --- | --- |
| 定位入口、版本与覆盖缺口 | [discovery.md](references/discovery.md) |
| 追踪候选、检查失败分支与跨系统组合 | [reasoning.md](references/reasoning.md)；按需补 [surfaces.md](references/surfaces.md) |
| 存档、资产、奖励、收据或恢复 | [persistence.md](references/persistence.md) |
| 危险效果经过第三方库 | [dependencies.md](references/dependencies.md) |
| 推导可能的恶意利用 | [abuse-analysis.md](references/abuse-analysis.md) |
| 归类、反证与隔离验证 | [validation.md](references/validation.md) |
| 需要多 agent 分工 | [orchestration.md](references/orchestration.md) |
| 交付报告或向修复任务交接 | [reporting.md](references/reporting.md)；生成图时再读 [diagrams.md](references/diagrams.md) |

只需文本或用户要求修复时，可由已安装的 `bsa-lite` 承接；后者按需复用本目录指引。保留发现 ID、版本与证据缺口，不能把“完成修改”直接当作“验证已修复”。
