# V6 阶段D联调与综合回归清单

## 1. 文档定位
- 文档状态：`生效`
- 目标：在阶段 C 收口闭合后，冻结阶段 D 的联调范围、环境基线、责任边界、关键链路与回归出口，避免在联调阶段再次插入新功能开发。
- 使用边界：本清单用于阶段 D 联调与综合回归，不替代 `docs/需求方案.md`、`docs/V6阶段B-详细设计与原型冻结包.md` 与各模块任务包。

## 2. 当前阶段判定
- 当前阶段：`阶段 D - 联调与综合回归（执行中）`
- 进入条件：`M1 ~ M7`、`M8-01 ~ M8-28` 已完成并推送，且已完成阶段 C 冻结范围闭合复核、联调范围与真实交付范围一致、降级事项已写入阶段 E 或后续治理池。
- 当前唯一主目标：`D-01 联调与综合回归执行`
- 当前结论：阶段 C 冻结范围闭合复核已通过，本清单自本轮起作为阶段 D 执行基线。
- 当前自动化基线：已完成首轮自动化回归、稳定性复核与 `D-CHAIN-01`、`D-CHAIN-02`、`D-CHAIN-03`、`D-CHAIN-04`、`D-CHAIN-05`、`D-CHAIN-06` 定向回归，后端全量 `137 passed`、`D-CHAIN-01` 定向后端回归 `25 passed`、`D-CHAIN-02` 定向后端回归 `24 passed`、`D-CHAIN-03` 定向后端回归 `15 passed`、`D-CHAIN-04` 定向后端回归 `10 passed`、`D-CHAIN-05` 定向后端回归 `17 passed`、`D-CHAIN-06` 定向后端回归 `30 passed`、管理后台 `pnpm test` 当前为 `86 passed`、`pnpm build` 通过、小程序 `node --test tests/*.test.js` 当前为 `58 passed`；详见 `docs/history/stage-d/V6阶段D-D01联调执行记录-2026-03-08.md`。

## 3. 联调范围冻结

| 范围 | 本轮纳入 | 说明 |
|---|---|---|
| 后端主链接口 | 是 | 覆盖权限、订单、资金、库存、合同关闭、报表、重算与审计 |
| 管理后台 | 是 | 覆盖登录、仪表盘、业务看板、合同管理台、订单、资金、库存、合同关闭、退款核销、多维报表、导出任务、汇总重算 |
| 小程序 | 是 | 覆盖本地联调/微信登录、轻量报表、消息、待办、供应商采购单相关首批能力 |
| 数据与审计 | 是 | 覆盖业务审计日志、报表快照、导出任务、重算任务、扫描留痕；不包含 `ADM-AUDIT-01` 独立审计日志中心页面 |
| 新业务规则开发 | 否 | 阶段 D 不新增业务规则，不再扩展页面或接口范围 |
| 新口径版本/历史回算 | 否 | 不新增 `v2/v3` 口径，不进入历史日期回算 |

## 4. 联调环境与角色基线

| 维度 | 冻结口径 |
|---|---|
| 后端环境 | `Conda jgport` + `FastAPI` + `PostgreSQL 18` |
| 管理后台模式 | `demo/proxy` 双模式保留，阶段 D 以 `proxy` 实联调为主，`demo` 仅用于空态与只读演示兜底 |
| 小程序模式 | 本地联调与微信登录链路都需回归，优先验证本地联调可稳定切换身份 |
| 角色范围 | 管理后台 Web 仅 `operations`、`finance`、`admin`；小程序/后端联调覆盖 `customer`、`supplier`、`warehouse` |
| 数据要求 | 开发/联调新增数据必须带 `CODEX-TEST-`、`AUTO-TEST-` 或同批次唯一前缀 |
| 数据清理 | 联调完成后按特殊标识定向清理，不得扩大范围误删手工测试数据 |

## 5. 关键联调主链

| 链路ID | 链路名称 | 上游输入 | 关键验证点 | 主要页面/接口 |
|---|---|---|---|---|
| D-CHAIN-01 | 合同到订单审批主链 | 合同管理台创建/提审/审批，销售合同生效、客户下单 | 合同创建、提交审批、审批驳回回退后修改再提审、审批生效、订单创建/提交、运营审批、财务审批、销售转采购成功，权限阻断正确 | `ContractsView`、`OrdersView`、合同/订单相关接口 |
| D-CHAIN-02 | 收付款处理主链 | 审批后单据生成 | 待补录、确认、凭证路径、退款申请/审核/驳回、核销状态一致 | `FundsView`、`FundsReconcileView` |
| D-CHAIN-03 | 仓储执行主链 | 采购/销售单据已可执行 | 入库、出库、校验失败、仓库身份边界、数量履约累计一致 | `InventoryView` |
| D-CHAIN-04 | 合同关闭主链 | 数量履约完成且资金条件满足 | 自动关闭、手工关闭、差异展示、关闭后阻断一致 | `ContractCloseView` |
| D-CHAIN-05 | 汇总报表主链 | 订单/资金/库存/关闭数据已变化 | 仪表盘、业务看板、轻量报表、多维报表、导出任务、汇总重算、扫描告警口径一致 | `OverviewView`、`TasksView`、`ReportsMultiDimView`、`ReportExportTasksView`、`ReportRecomputeTasksView` |
| D-CHAIN-06 | 小程序与身份主链 | 本地联调/微信登录身份 | 登录、会话续期、轻量报表、待办消息、供应商采购单能力可用且权限正确 | 小程序登录/报表/订单相关页面 |

## 6. 综合回归矩阵

### 6.1 后端自动化回归

| 回归项 | 对应测试 |
|---|---|
| 权限、阈值、审计基线 | `backend/tests/test_m1_access.py`、`backend/tests/test_m1_thresholds.py`、`backend/tests/test_m1_audit.py` |
| `D-CHAIN-01` 合同到订单审批主链 | `backend/tests/test_d01_contract_order_chain.py` |
| `D-CHAIN-02` 收付款处理主链 | `backend/tests/test_d01_funds_chain.py` |
| `D-CHAIN-03` 仓储执行主链 | `backend/tests/test_d01_inventory_chain.py` |
| `D-CHAIN-04` 合同关闭主链 | `backend/tests/test_d01_contract_close_chain.py` |
| `D-CHAIN-05` 汇总报表主链 | `backend/tests/test_d01_reports_chain.py` |
| `D-CHAIN-06` 小程序与身份主链 | `backend/tests/test_d01_mini_identity_chain.py` |
| 合同主链 | `backend/tests/test_m2_contracts.py` |
| 订单主链 | `backend/tests/test_m3_orders.py` |
| 资金主链 | `backend/tests/test_m4_funds.py` |
| 库存主链 | `backend/tests/test_m5_inventory.py` |
| 合同关闭主链 | `backend/tests/test_m6_contract_close.py` |
| 报表、导出、扫描、重算 | `backend/tests/test_m7_reports.py` |
| 小程序与供应商首批能力 | `backend/tests/test_m8_mini_auth.py`、`backend/tests/test_m8_wechat_auth.py`、`backend/tests/test_m8_mini_orders.py`、`backend/tests/test_m8_supplier_purchase_orders.py` |

### 6.2 管理后台自动化回归

| 回归项 | 对应测试/构建 |
|---|---|
| 工具与权限 | `admin-web/src/utils/auth.spec.ts`、`admin-web/src/utils/permissions.spec.ts`、`admin-web/src/utils/report-drill.spec.ts`、`admin-web/src/router/index.spec.ts` |
| mock 与报表演示链 | `admin-web/src/mock/*.spec.ts`、`admin-web/src/stores/report.spec.ts` |
| 页面关键交互 | `admin-web/src/views/contracts/ContractsView.spec.ts`、`admin-web/src/views/orders/OrdersView.spec.ts`、`admin-web/src/views/funds/FundsView.spec.ts`、`admin-web/src/views/funds/FundsView.actions.spec.ts`、`admin-web/src/views/funds-reconcile/FundsReconcileView.spec.ts`、`admin-web/src/views/funds-reconcile/FundsReconcileView.actions.spec.ts`、`admin-web/src/views/inventory/InventoryView.spec.ts`、`admin-web/src/views/contract-close/ContractCloseView.spec.ts`、`admin-web/src/views/dashboard/OverviewView.spec.ts`、`admin-web/src/views/board/TasksView.spec.ts`、`admin-web/src/views/reports-multi-dim/ReportsMultiDimView.spec.ts`、`admin-web/src/views/report-export-tasks/ReportExportTasksView.spec.ts`、`admin-web/src/views/report-recompute-tasks/ReportRecomputeTasksView.spec.ts` |
| 构建门禁 | `pnpm test`、`pnpm build` |

### 6.3 小程序自动化回归

| 回归项 | 对应测试/校验 |
|---|---|
| 语法校验 | `node --check app.js config/env.js mocks/order.js utils/api.js utils/format.js utils/light-report.js utils/message.js utils/navigation.js utils/order.js utils/request.js utils/session.js utils/supplier-purchase.js utils/todo.js utils/warehouse-exec.js pages/login/index.js pages/todo/index.js pages/msg/index.js pages/order/index.js pages/report/index.js pages/exec/index.js pages/supplier-purchase/index.js` |
| 登录与会话 | `miniprogram/tests/session.test.js`、`miniprogram/tests/login-page.test.js` |
| 待办与消息 | `miniprogram/tests/todo.test.js`、`miniprogram/tests/message.test.js`、`miniprogram/tests/todo-page.test.js`、`miniprogram/tests/message-page.test.js` |
| 经营快报与权限边界 | `miniprogram/tests/light-report.test.js`、`miniprogram/tests/report-page.test.js` |
| 页面导航与业务页 | `miniprogram/tests/navigation.test.js`、`miniprogram/tests/order.test.js`、`miniprogram/tests/warehouse-exec.test.js`、`miniprogram/tests/supplier-purchase.test.js`、`miniprogram/tests/supplier-purchase-page.test.js` |

### 6.4 手工联调回归

| 手工项 | 重点确认 |
|---|---|
| 管理后台全页回看 | 页面路由、角色按钮、空态、错误态、中文提示一致 |
| 小程序角色切换 | 本地联调身份切换、会话续期、角色阻断与报表可见性正确 |
| 端到端经营链路 | 订单、资金、库存、关闭、报表指标在同一批测试数据下可追溯 |
| 审计与追溯 | 业务日志、报表快照、导出任务、重算任务、扫描留痕可回看 |

- 手工联调执行入口与核对模板详见 `docs/history/stage-d/V6阶段D-手工联调检查清单-2026-03-08.md`。

## 7. 业务视角联调评估原则
- 业务可执行性：必须验证运营、财务、仓库、客户、供应商在当前首批边界下都能完成各自允许动作，不能出现“页面可见但链路无法执行”的假闭环。
- 运营效率与成本：重点检查是否仍存在重复录入、跨页跳转断裂、任务中心回看困难等高频低效点。
- 运输与仓储安全风险：重点验证入库/出库状态、校验失败、履约滞留与异常提示是否及时、准确、可追踪。
- 合规性、可审计性与可追溯性：重点验证审批、确认、关闭、导出、重算、扫描相关留痕是否完整且可按测试标识回查。
- 实施复杂度与迭代优先级：阶段 D 只记录问题并分级，不直接插入新功能开发；阻断发布的问题进入阶段 E 前必须清零。

## 8. 出口门禁
- 自动化回归通过：后端、前端测试与构建全部通过。
- 手工联调完成：关键主链与高风险角色链路至少完成一轮实联调。
- 问题分级清晰：不存在阻断问题，不存在未定责问题，不存在未归档的一致性争议。
- 文档闭环完成：联调结论、遗留问题、验收输入同步回写阶段 D/E 文档。

## 9. 本轮非目标
- 不新增业务规则、页面能力、接口能力或数据库模型。
- 不在阶段 D 内再次拆分新的 `M8-xx` 功能任务包。
- 不把联调问题处理成无边界的需求扩张；超出当前冻结范围的事项统一进入阶段 E 前的遗留池评估。
