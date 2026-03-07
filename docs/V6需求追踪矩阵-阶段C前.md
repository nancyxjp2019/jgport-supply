# V6 需求追踪矩阵（阶段C前）

## 1. 目的与门槛
- 目的：验证需求是否被完整理解并可直接进入模块开发。
- 门槛：
  - 规则覆盖率 `100%`（规则1~53全部映射）。
  - 规则冲突数 `0`。
  - 阻断级未决问题 `0`。

## 2. 追踪矩阵（规则 -> 设计 -> 实现 -> 验证）

| 规则ID | 规则摘要 | 模块 | 页面/交互 | API/触发 | 数据对象 | 验证用例 |
|---|---|---|---|---|---|---|
| 1 | V6独立工程重建 | 治理 | - | - | 目录`jgport/` | GOV-001 |
| 2 | V5归档到`archive/v5` | 治理 | - | - | 归档目录 | GOV-002 |
| 3 | 生产全新库部署 | 运维 | - | 部署流程 | 全新DB实例 | OPS-001 |
| 4 | 分阶段迁移顺序 | 项目管理 | - | 里程碑门禁 | M1~M8计划 | PM-001 |
| 5 | 合规审计连续性 | M1/审计 | ADM-AUDIT-01 | 全关键动作写审计 | `business_audit_logs` | AUD-001 |
| 6 | 金额单据中台化 | M4 | ADM-PAYMENT-01/ADM-RECEIPT-01 | `/payment-docs/*` `/receipt-docs/*` | `payment_docs`,`receipt_docs` | FIN-001 |
| 7 | 数量单据中台化 | M5 | ADM-INBOUND-01/ADM-OUTBOUND-01 | `/inbound-docs/*` `/outbound-docs/*` | `inbound_docs`,`outbound_docs` | INV-001 |
| 8 | 采购合同生效触发付款单+入库草稿 | M2+M4+M5 | 合同审批页 | `/contracts/{id}/approve` 写入下游待处理任务 | `contracts` + `contract_effective_tasks` + 付款单/入库单 | TRG-001 |
| 9 | 销售合同生效触发收款单保证金 | M2+M4 | 合同审批页 | `/contracts/{id}/approve` 写入下游待处理任务 | `contracts` + `contract_effective_tasks` + 收款单 | TRG-002 |
| 10 | 销售订单财务通过自动三单 + 订单关闭条件冻结 | M3+M4+M6 | ADM-ORDER-S-01/ADM-ORDER-P-01 | `/sales-orders/{id}/finance-approve` + 订单完成判定 | `sales_orders` + `purchase_orders` + `sales_order_derivative_tasks` + 出库累计 | TRG-003 |
| 11 | 销售衍生采购订单付款=0无条件放行 | M3+M4 | ADM-ORDER-P-01 | `po_zero_pay_exception`触发 | `purchase_orders.zero_pay_exception_flag` + `sales_order_derivative_tasks` | EXC-001 |
| 12 | 出库双通道（系统+手工）+ 履约累计幂等防重 | M5+M6 | ADM-OUTBOUND-01 | `/outbound-docs/manual` + 仓库出库事件 + 生效累计任务 | `outbound_docs` + `contract_qty_effects` + `doc_relations` | INV-002 |
| 13 | 双阈值模型与约束（系统级统一下发） | M1+M2+M6 | ADM-CONFIG-01 | `/system-configs/thresholds` + 合同生效写快照 | `system_configs` + `contracts.threshold_*_snapshot` | CFG-001 |
| 14 | 零金额免凭证（规则14场景） | M4 | ADM-RECEIPT-01/ADM-PAYMENT-01 | `/receipt-docs/{id}/confirm` `/payment-docs/{id}/confirm` | 收付款单免凭证字段 + 阈值校验结果 | EXC-002 |
| 15 | 单价来自合同，实收实付来自单据，附件按单据分层归属 | M3+M4 | ADM-ORDER-S-01 | 订单创建/财务确认/附件上传 | `sales_orders.unit_price` + 收付款单 + `doc_attachments` | FIN-002 |
| 16 | 数量履约完成状态 + 完成后禁止新增出入库生效 | M5+M6 | 合同详情状态流 | 履约计算任务 + 出入库生效阻断 | `contract_items.qty_in_acc/qty_out_acc` + 合同状态 | CLS-001 |
| 17 | 金额闭环采购/销售分开 + 保证金净额伪代码口径 | M4+M6 | 合同详情闭环面板 | 自动关闭校验任务 | 收付款单净额字段 + 退款字段 | CLS-002 |
| 18 | 自动关闭与手工关闭边界 | M6 | 合同详情手工关闭 | `/contracts/{id}/manual-close` | 合同状态+关闭字段 | CLS-003 |
| 19 | 手工关闭五步处理顺序 | M6 | 手工关闭确认弹窗 | 关闭事务编排 | 差异记录/终止记录 | CLS-004 |
| 20 | 合同履约数量上限 | M5+M6 | 入库/出库提交页 | `/inbound-docs/{id}/submit` `/outbound-docs/{id}/submit` | 阈值校验结果 | INV-003 |
| 21 | 单据上下游可追溯 + 双通道唯一键防重 | M1+M5+M6 | ADM-TRACE-01 | 图谱查询API + 防重累计流水 | `doc_relations` + `contract_qty_effects` | AUD-002 |
| 22 | 当前版本低并发策略 | NFR | - | 幂等+事务，不用分布式锁 | `source_event_id`,`幂等键` | NFR-001 |
| 23 | 全新库初始化清单 | M1 | ADM-CONFIG-01 | 初始化脚本与校验 | 主数据/字典/参数 | OPS-002 |
| 24 | 后台全量、小程序轻量 | M8 | 端能力矩阵 | 菜单与权限路由 | 角色权限表 | UXR-001 |
| 25 | 小程序功能边界（客户/供应商/仓库仅小程序） | M8 | MINI-* | 小程序接口白名单 + 后台登录禁用策略 | 小程序菜单权限 + 后台登录策略 | UXR-002 |
| 26 | 后台必须有仪表盘+看板 | M7 | ADM-DASH-01/ADM-BOARD-01 | `/dashboard/summary` `/boards/tasks` | 指标快照 | RPT-001 |
| 27 | 报表分层（小程序轻量/后台多维） | M7 | MINI-REPORT-01 + 后台报表页 | 轻量/多维报表接口 | 报表口径字典 | RPT-002 |
| 28 | 报表SLA与口径冻结 | M7 | 仪表盘口径提示 | SLA监控+口径版本参数 | `report_snapshots.version` | RPT-003 |
| 29 | 报表混合生成机制 + 每日闭环/履约扫描告警 | M6+M7 | 报表任务监控/业务看板 | 事件增量+定时校准+每日扫描任务 | 报表任务 + 扫描审计日志 + 告警快照 | RPT-004 |
| 30 | 小程序仅看驳回结果 | M8 | MINI-ORDER-01 | 小程序禁用驳回动作 | 端权限配置 | UXR-003 |
| 31 | 仪表盘首版四指标冻结 | M7 | ADM-DASH-01 | `/dashboard/summary` | 指标定义版本 | RPT-005 |
| 32 | 非目标：多活/跨地域容灾 | NFR范围 | - | - | 架构范围声明 | SCOPE-001 |
| 33 | 非目标：完整财务核算体系 | 业务范围 | - | - | 产品边界声明 | SCOPE-002 |
| 34 | 终端用户可见信息统一中文显示 | M8+M7 | `ADM-*` + `MINI-*` 全页面提示文案 | 前端消息映射层 + 表单校验提示 + 阻断提示渲染 | 前端文案资源与错误消息映射 | UXR-004 |
| 35 | 管理后台Web登录边界与后端接口授权分层 | M1+M8 | 管理后台登录页 + 全接口鉴权链路 | 登录鉴权中间件 + 角色/公司范围校验 | 登录身份上下文 + 角色权限策略 | SEC-001 |
| 36 | 合同早期状态机（草稿->待审批->生效中；驳回回草稿） | M2 | 合同创建页/审批页 | `/contracts/purchase` `/contracts/sales` `/contracts/{id}/submit` `/contracts/{id}/approve` | `contracts.status` + 合同审批审计 | CT-001 |
| 37 | 销售订单审批状态机与驳回回退 | M3 | MINI-ORDER-01 / ADM-ORDER-S-01 | `/sales-orders` `/sales-orders/{id}` `/sales-orders/{id}/submit` `/sales-orders/{id}/ops-approve` `/sales-orders/{id}/finance-approve` | `sales_orders.status` + 订单审批审计 | ORD-001 |
| 38 | 销售订单财务审批必须绑定采购合同 | M3 | ADM-ORDER-S-01 / ADM-ORDER-P-01 | `/sales-orders/{id}/finance-approve` | `purchase_orders.purchase_contract_id` + `sales_order_derivative_tasks` | ORD-002 |
| 39 | 出库单执行前置状态门禁 | M3+M5 | MINI-WH-OUTBOUND-01 / ADM-EXEC-01 | `/outbound-docs/warehouse-confirm` `/outbound-docs/manual` | `sales_orders.status` + `outbound_docs` | INV-004 |
| 40 | 合同关闭收口规则 | M4+M5+M6 | ADM-CONTRACT-CLOSE-01 | 自动关闭任务 + `/contracts/{id}/manual-close` | 收付款/出入库状态 + 关闭审计 | CLS-005 |
| 41 | 仪表盘首版指标口径冻结（执行范围/自然日/30日窗口/v1） | M7 | ADM-DASH-01 / MINI-REPORT-01 | `/dashboard/summary` `/reports/light/overview` | `report_snapshots.version` + 仪表盘/轻报表指标快照 | RPT-006 |
| 42 | 供应商移动端首批真实业务页边界 | M8 | MINI-SUPPLIER-PO-01 | `/supplier/purchase-orders` `/supplier/purchase-orders/{id}` | 供应商采购订单列表/详情 | MINI-SUP-001 |
| 43 | 供应商附件回传首批开放边界 | M8 | MINI-SUPPLIER-PO-01 | `/supplier/purchase-orders/{id}/attachments` | `doc_attachments` + 采购订单附件标签 | MINI-SUP-002 |
| 44 | 供应商发货确认首批开放边界 | M8 | MINI-SUPPLIER-PO-01 | `/supplier/purchase-orders/{id}/confirm-delivery` | 采购订单确认留痕字段 | MINI-SUP-003 |
| 45 | 供应商付款校验结果回看首批开放边界 | M8 | MINI-SUPPLIER-PO-01 | `/supplier/purchase-orders/{id}` 付款校验结果字段 | 采购订单状态 + `zero_pay_exception_flag` + 说明字段 | MINI-SUP-004 |
| 46 | M8后台迁移优先级基线 | 项目管理/M8 | - | `M8-16+` 路线冻结与任务包拆分 | 路线文档 + 页面级任务包 | PM-002 |
| 47 | 运营订单处理台首批开放边界 | M8 | ADM-ORDER-OPS-01 | `/sales-orders` `/sales-orders/{id}` `/sales-orders/{id}/ops-approve` `/sales-orders/{id}/finance-approve` | 销售订单审批字段 + 处理台页面 | ORD-003 |
| 48 | 财务资金处理台首批开放边界 | M8 | ADM-FUNDS-01 | `/payment-docs/*` `/receipt-docs/*` + 资金处理台任务包 | `payment_docs`,`receipt_docs`,`doc_attachments` | FIN-003 |
| 49 | 库存执行跟踪台首批开放边界 | M8 | ADM-INVENTORY-01 | `/inbound-docs` `/inbound-docs/{id}` `/outbound-docs` `/outbound-docs/{id}` + 跟踪台任务包 | `inbound_docs`,`outbound_docs` | INV-005 |
| 50 | 合同关闭差异台首批开放边界 | M8 | ADM-CONTRACT-CLOSE-02 | `/contracts` `/contracts/{id}` `/contracts/{id}/manual-close` + 差异台任务包 | `contracts`,`contract_items`,`contract_effective_tasks` | CLS-006 |
| 51 | 退款核销与资金驳回台首批开放边界 | M8 | ADM-FUNDS-RECON-01 | `/payment-docs/{id}/refund-*` `/receipt-docs/{id}/refund-*` `/payment-docs/{id}/writeoff` `/receipt-docs/{id}/writeoff` + 退款核销台任务包 | `payment_docs`,`receipt_docs`,`business_audit_logs` | FIN-004 |
| 52 | 多维报表与导出首批开放边界 | M8 | ADM-REPORT-MULTI-01 | `/reports/admin/multi-dim` `/reports/admin/multi-dim/export` + 多维报表任务包 | `report_snapshots`,`payment_docs`,`receipt_docs` | RPT-007 |
| 53 | 管理后台按钮级权限首批开放边界 | M8 | ADM-PERM-BTN-01 | 管理后台关键动作按钮权限映射与页面收口 + 按钮权限任务包 | `auth_session`,`前端按钮权限映射` | SEC-002 |

## 3. 验收方式
- 抽检方式：随机抽取任意10条规则，要求能在“模块/页面/API/数据/测试”5列中完整追溯。
- 通过标准：
  - 任意抽检规则追溯成功率 `100%`。
  - 不允许出现“只在聊天里存在、文档未落地”的规则。

## 4. 使用说明
- 阶段C每个子模块开发前，先勾选本矩阵涉及规则，再开始编码。
- 若新增规则，必须先补充 `docs/需求方案.md`，再补本矩阵后才可开发。
