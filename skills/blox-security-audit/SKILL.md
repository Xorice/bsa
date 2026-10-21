---
name: blox-security-audit
description: 审计自有或获授权 Roblox 项目的可利用漏洞与交互逻辑缺陷。直接检查本地或 Studio 代码、第三方依赖及跨系统失败路径，支持多 agent 分工；输出有证据的发现、漏洞流程图或有覆盖依据的未发现结论。
license: MIT
---

# Blox Security Audit

从当前代码空间开始工作，交付可复核的审计结果。适用于不同项目结构与 agent；使用宿主提供的文件、搜索、Studio、委派能力，不依赖特定 MCP、框架、其他 skill 或付费服务。缺少某项能力时按下表降级，继续可做的分析。

任务定位是自有或获授权项目的防御性源码审计：找出缺陷、说明后果并提出修复。沿用本次请求及已有上下文中的项目与授权范围，不虚构授权，也不重复索要已明确的信息；默认只读源码，验证遵循 [validation.md](references/validation.md)。本声明不扩大操作权限。

本 skill 面向带流程图的完整审计交付。只需文本发现、向修复 agent 交接或按已有报告修复时，可使用同仓库独立安装的 `bsa-lite`；未安装时不依赖它完成本次任务。

## 工作顺序

1. **定位与建图**：读 [discovery.md](references/discovery.md)，原地搜索并按需读取实际运行源码，确定入口、资产和危险副作用，按相关生命周期建立覆盖账本；不以全量导出为前置步骤。
2. **推理与推广**：读 [reasoning.md](references/reasoning.md)，从业务不变量双向追踪，检查校验成功与失败分支的实际副作用，组合正常交互、失败和恢复路径；从一个缺口推广到相邻机制。
3. **并行深查**：有独立审计范围且支持 subagent 时，按 [orchestration.md](references/orchestration.md) 分工；否则串行执行相同问题。按下表只加载相关专项。
4. **反证与验证**：按 [validation.md](references/validation.md) 审核完整路径，统一候选分类，验证关键不变量，区分事实、模型和未证实影响。
5. **交付**：按 [reporting.md](references/reporting.md) 核对覆盖缺口、候选归类及可用历史发现，输出报告与覆盖理由；发现漏洞先直说直接后果、可能的恶意利用、成立前提与证据边界，再按 [diagrams.md](references/diagrams.md) 生成一份或多份紧凑流程图。

## 专项索引（按触发条件加载）

| 触发条件 | 读取 |
| --- | --- |
| 清点交互入口、战斗、物理、权限、资源消耗或跨服机制 | [surfaces.md](references/surfaces.md) |
| 任意持久化字段、货币/物品转移、奖励、收据、回档或迁移 | [persistence.md](references/persistence.md) |
| 评估缺陷如何被用来获利、破坏他人或扩散影响，撰写发现的影响提醒 | [abuse-analysis.md](references/abuse-analysis.md) |
| 网络暴露、存档、授权、动态加载等危险操作经过第三方库 | [dependencies.md](references/dependencies.md)，沿实际安装版调用链进入库内部 |
| 需要离线可视化 | [diagrams.md](references/diagrams.md)；内置标准库 Python 工具，无运行环境则输出 Mermaid 源码 |

## 结论底线

- 默认只读源工程，允许写本地审计产物。快照仅按需创建，避免模型把已返回的源码逐文件再抄写一遍。运行验证优先纯函数/内存桩；生产调用、真实资产/存档写入、压力测试不由本 skill 自动授权。Studio 不自动隔离真实服务。
- 追到实际校验与副作用；类型注解、客户端限制、模块名、成熟库和锁的存在均不能替代实现证据。找不到缺口也要主动寻找能阻断候选路径的防护证据。
- 搜索用于筛选与定位，对实际入口、危险效果和相关调用链阅读实现，必要时扩展；不把所有命中都全文复制。不要因找到一个漏洞就跳过剩余高风险范围，也不要为凑数量把假设升级为发现。
- 未发现时给出已检查路径、有效防护、失败路径证据和盲区；只能保证结论适用于所述版本与覆盖范围。源码不可用或关键链缺失时交付“审计不完整”，不能给出安全背书。
- 遇到宿主安全限制，按 [validation.md](references/validation.md) 保留证据与缺口并继续允许的工作；不得靠改写用途、伪造授权或换 agent 重试同一受限动作。
