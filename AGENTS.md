# 项目规则

## 交付与提交工作流（强制）

- 每次修改后，在最终交付前都要对所有变更文件进行自检。
- 每次任务完成后，必须在自检通过的基础上，再进行一次独立、全面的评审；若评审发现任何问题，必须先修复并重新执行“自检 -> 独立评审”循环，直至确认无问题后方可提交 Git。
- 最终交付时，必须明确汇报本次“自检 -> 独立评审”一共执行了几轮；若中途发现问题并进入修复闭环，需说明最终通过的是第几轮。
- 代码需改后需要对其对应的文档进行更新，若涉及业务规则和逻辑必须在需求方案文档中写明。如果文档中规则有冲突的地方必须明确后更正。
- 仅在自检通过后，编写清晰的中文 Git 提交信息，准确概括本次变更范围。
- 在同一个工作周期内完成 Git 提交，并推送到 GitHub 远端仓库（默认 `origin`）。
- 若远端推送失败，需先排查并修复问题，确认推送成功后再最终交付。
- 若自检未通过，先修复问题，再次自检通过后再提交。
- 因开发改动而生成的测试数据，在完成回归测试并确认通过后，必须及时清理；不得影响手工测试建立的数据，不得放任测试数据长期堆积。
- 因开发改动而生成的测试数据，必须在创建时就带统一且可检索的特殊标识；推荐在用户名、公司编码、仓库编码、油品编码、合同号、模板编码、附件路径或业务备注中统一使用 `AUTO-TEST-`、`CODEX-TEST-` 或同一批次唯一前缀，禁止生成无法区分来源的“裸数据”。
- 完成回归测试后，必须优先依据上述特殊标识进行定向清理；若无法确认某批数据是否带有该标识，则不得直接扩大范围删除，以免误删手工测试数据。

## 技能调用规则（强制）

- 默认执行时必须先匹配并调用可用技能；除非确认无相关技能可调用，才允许使用通用流程直接处理。
- 用户明确点名技能时，必须调用该技能执行，不得跳过。
- 任务可匹配多个技能时，必须使用“最小必要技能集合”完成目标，并在执行中说明调用顺序与原因。
- 若技能不可用（缺失、损坏、权限受限或不适配当前任务），必须明确说明原因，并提供可验证的替代方案继续完成任务。

## 交付前质量门禁（强制）

- 自检必须覆盖本次所有变更文件，至少包含：代码审查、对应测试执行、关键流程回归、文档一致性检查。
- 独立评审必须与自检分开执行，评审结论需覆盖本次所有变更文件，并以“无阻断问题、无高优先级问题、无未处理的一致性问题”为提交前通过标准。
- 独立评审记录必须能回溯每一轮的结论与总循环次数，最终交付时需对外汇报。
- 涉及业务规则新增、调整、停用时，必须先更新 `docs/需求方案.md` 并标注状态为 `生效`、`弃用` 或 `规划中`。
- 仅在质量门禁全部通过后，才允许进入提交与推送环节。

## 大型需求开发流程（强制）

- 对于大型需求，必须按标准阶段推进：需求冻结 -> 原型与交互评审 -> 技术方案评审 -> 模块拆分 -> 分迭代开发 -> 联调回归 -> 验收发布。
- 在需求未冻结前，禁止进入功能开发；仅允许进行需求澄清、原型设计、方案设计与风险评审。
- 开发必须按模块或子模块逐步推进；单次迭代只允许聚焦一个模块或同一模块下的一个子模块，禁止一次性跨多个核心模块并行大改。
- 每个模块开发前必须先定义上下游边界（输入、输出、依赖、状态流转、失败回滚）；未定义边界不得开工。
- 每个模块完成后必须通过该模块独立门禁（功能自测、关键流程回归、文档更新）后，才能进入下一个模块，避免上下文丢失与后续返工。

## 业务视角（强制）

- 所有需求分析与方案设计，必须从以下组合视角进行思考：
  - 成品油批发运营
  - 油库管理
  - 供应链协同
  - 油品运输执行
  - 安全生产与监管合规
- 每次输出都要围绕以下重点评估需求：
  - 业务可执行性
  - 运营效率与成本
  - 运输与仓储安全风险
  - 合规性、可审计性与可追溯性
  - 实施复杂度与迭代优先级
- 管理后台和小程序等页面设计原则
  - 简洁 + 功能优先，符合人类用户操作习惯和感观
  - 移动友好 & 可读性，一致性 & 高效操作
  - 强数据可视化 + 实时性

## 代码注释语言（强制）

- 所有代码注释、备注、说明性注解统一使用中文。
- 新增代码时不得写英文注释；修改旧代码时如发现英文注释需同步改为中文（第三方库源码或协议关键字除外）。

## Markdown 文档语言（强制）

- 所有产出物为 `.md` 的文档，正文内容统一使用中文。
- 允许保留必要的英文技术关键字（如 API 路径、命令、库名、协议名），但解释说明必须使用中文。

## 业务规则文档基线（强制）

- 所有业务规则新增、调整、停用，必须先更新 `docs/需求方案.md`，不得仅停留在聊天记录、测试口径、代码注释或临时文档中。
- `docs/需求方案.md` 中的业务规则必须标注当前状态，统一使用：`生效`、`弃用`、`规划中`。
- 未写入 `docs/需求方案.md` 且未标注状态的业务口径，一律不得作为开发、测试、验收和交付依据。

## V5归档技术栈（只读基线）

- 归档路径：`archive/v5/`

- 后端框架与运行：
  - `Python` + `FastAPI`（`archive/v5/backend/requirements.txt` 当前版本：`0.128.4`）
  - `Uvicorn`（`uvicorn[standard]`，当前版本：`0.40.0`）
  - API 组织方式：RESTful 风格，统一前缀 `/api/v1`
- 数据层：
  - ORM：`SQLAlchemy 2.0.46`
  - 迁移：`Alembic 1.18.3`
  - 默认数据库：`SQLite`（`database_url=sqlite:///./data/app.db`），已启用 `WAL`、`foreign_keys=ON`
  - 可切换数据库驱动：`PyMySQL 1.1.2`（用于 MySQL 场景）
- 配置与安全：
  - 配置管理：`pydantic-settings 2.12.0`（`.env` 驱动）
  - 鉴权：JWT（`python-jose 3.5.0`）
  - 密码哈希：`passlib 1.7.4`（`pbkdf2_sha256`）
  - MFA：基于 TOTP 协议的自研实现（含恢复码）
- 文件与报表能力：
  - 上传解析：`python-multipart 0.0.22`
  - PDF 生成：`reportlab 4.4.4`（合同/发货指令单等）
  - Excel 导出：`openpyxl 3.1.5`
  - 对象存储：本地文件系统（默认）+ 阿里云 OSS（`oss2`）
- 终端与前端：
  - 微信小程序：原生 `WXML + WXSS + JavaScript`（`archive/v5/miniprogram/project.config.json` 当前 `libVersion=3.7.8`）
  - 小程序网络层：基于 `wx.request` / `wx.uploadFile` 封装
  - 后台管理端：`HTML + CSS + 原生 JavaScript` 单页管理台（无 React/Vue 依赖）
- 测试与质量保障：
  - 后端测试：`pytest 9.0.2`
  - UAT 自动化：`Playwright`（Node.js，当前版本 `^1.54.2`，位于 `archive/v5/tests/uat`）
- 部署与运维：
  - 部署方式：以 Linux Shell 脚本为主（`deploy/`）
  - Web 网关：`Nginx`（仓库提供限流与防护脚本）
  - 运行日志：文件日志 + 数据库业务审计日志（`business_logs`）

## V6项目基座技术栈（`jgport`）

- 目录：仓库根目录（`backend/`、`admin-web/`、`miniprogram/`、`docs/`）
- 后台前端：`Vue 3 + Element Plus + Vben Admin`
- 后端：`Python + FastAPI`（沿用 V5 业务域与 API）
- 数据库：`PostgreSQL 18`（截至 2026-03-05 的最新主版本，作为新项目默认基线）
- Python 开发环境：Conda 环境 `jgport`
- 小程序：保留原生小程序执行链基座，默认不迁入 UAT 自动化代码

## V6文档维护要求（强制）

- 新项目技术栈、部署基线发生变化时，需同步更新：
  - `README.md`
  - `docs/新项目重建基座说明-Vue3-Vben-Postgres.md`
  - `backend/README.md`

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **jgport** (5797 symbols, 13711 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/jgport/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/jgport/context` | Codebase overview, check index freshness |
| `gitnexus://repo/jgport/clusters` | All functional areas |
| `gitnexus://repo/jgport/processes` | All execution flows |
| `gitnexus://repo/jgport/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## CLI

- Re-index: `npx gitnexus analyze`
- Check freshness: `npx gitnexus status`
- Generate docs: `npx gitnexus wiki`

<!-- gitnexus:end -->
