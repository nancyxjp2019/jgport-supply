# V6 阶段B交付件：详细设计与原型冻结包（草稿）

## 1. 文档定位
- 文档状态：`已冻结`
- 目标：冻结实现口径，形成可开发规格，作为阶段C模块开发唯一输入。
- 上游输入：
  - `docs/需求方案.md`（当前规则 `1~39` 与“业务目标/角色权限”基线）
  - `docs/V6阶段A-流程图状态机与UI原型清单.md`
- 下游输出：阶段C模块任务拆分、接口开发、联调与测试用例。

## 2. 冻结范围与边界
- 本文冻结：
  - 核心数据模型与关键约束。
  - 业务触发矩阵、幂等策略、失败补偿策略。
  - API字段口径、校验规则、错误码与审计字段。
  - 原型页面清单、字段字典、交互动作字典。
- 本文不冻结：
  - 数据库物理分区、索引微调、性能参数微调。
  - 非阻断类UI视觉细节（颜色、间距微调）。
- 本文非目标（当前版本不做）：
  - 分布式锁与高并发强一致控制。
  - 多活与跨地域容灾体系。
  - 完整财务核算体系（总账、成本、税务）。

## 2.1 角色与公司归属冻结
- 业务角色：客户、运营、财务、供应商、仓库；系统管理员归属运营商公司。
- 公司绑定：客户->客户公司，供应商->供应商公司，仓库->仓库公司，运营/财务/管理员->运营商公司。
- 权限实现：所有接口按“角色+公司范围”双维校验，防止跨公司越权读取或写入。
- 端登录边界：客户、供应商、仓库角色不开放管理后台 Web 登录，仅通过小程序端处理业务。
- 分层约束：管理后台 Web 登录权限不等价于后端接口授权；服务端仍需对每个接口执行身份、角色、公司范围与能力校验。
- 鉴权上下文：受保护接口统一从服务端身份上下文读取 `user_id`、`role_code`、`company_id`、`company_type`、`client_type`，不得信任请求体自带操作者身份字段。

## 3. 数据模型详细设计（逻辑模型）

## 3.1 核心实体清单

| 实体 | 关键字段 | 关键约束 | 说明 |
|---|---|---|---|
| `contracts` | `id`,`contract_no`,`direction`,`status`,`threshold_release_snapshot`,`threshold_over_exec_snapshot`,`close_type`,`manual_close_reason` | `contract_no`唯一；`direction`审批后不可变；阈值快照来自系统参数且`release <= over_exec` | 合同主表，区分采购/销售方向 |
| `contract_items` | `id`,`contract_id`,`oil_product_id`,`qty_signed`,`unit_price`,`qty_in_acc`,`qty_out_acc` | `contract_id+oil_product_id`唯一 | 合同按油品明细，金额与数量计算基准 |
| `contract_effective_tasks` | `id`,`contract_id`,`target_doc_type`,`status`,`idempotency_key`,`payload_json` | `idempotency_key`唯一；合同审批通过时自动写入待处理任务 | 合同生效后待生成下游单据的任务表 |
| `sales_orders` | `id`,`order_no`,`sales_contract_id`,`status`,`unit_price`,`qty_ordered` | `unit_price`来自销售合同，不允许脱离合同重写 | 销售订单主表 |
| `purchase_orders` | `id`,`order_no`,`purchase_contract_id`,`source_sales_order_id`,`payable_amount`,`zero_pay_exception_flag` | `source_sales_order_id`必填（销售衍生场景）；`zero_pay_exception_flag`仅在规则11场景为真 | 采购订单主表 |
| `sales_order_derivative_tasks` | `id`,`sales_order_id`,`target_doc_type`,`status`,`idempotency_key`,`payload_json` | `idempotency_key`唯一；财务审批通过时自动写入收付款待处理任务 | 销售订单财务审批后的下游任务表 |
| `receipt_docs` | `id`,`doc_no`,`doc_type`,`contract_id`,`sales_order_id`,`amount_actual`,`voucher_required`,`voucher_exempt_reason`,`refund_status`,`refund_amount`,`status` | 手工录入必须有`contract_id`；`amount_actual=0`且免凭证时必须有原因 | 收款单（含保证金退款口径） |
| `payment_docs` | `id`,`doc_no`,`doc_type`,`contract_id`,`purchase_order_id`,`amount_actual`,`voucher_required`,`voucher_exempt_reason`,`refund_status`,`refund_amount`,`status` | 手工补录必须同时关联`contract_id + purchase_order_id` | 付款单（含保证金退款口径） |
| `inbound_docs` | `id`,`doc_no`,`contract_id`,`purchase_order_id`,`oil_product_id`,`warehouse_id`,`source_type`,`idempotency_key`,`actual_qty`,`status` | 采购合同按油品明细逐条生成；生效前必须通过合同超量履约阈值校验；`idempotency_key`唯一 | 入库单 |
| `outbound_docs` | `id`,`doc_no`,`contract_id`,`sales_order_id`,`oil_product_id`,`warehouse_id`,`source_type`,`source_ticket_no`,`manual_ref_no`,`idempotency_key`,`actual_qty`,`status` | 系统出库与手工补录均需绑定销售合同并通过超量校验；`idempotency_key`唯一 | 出库单 |
| `contract_qty_effects` | `id`,`contract_item_id`,`doc_type`,`doc_id`,`effect_type`,`effect_qty`,`idempotency_key` | 唯一键：`contract_item_id + doc_type + doc_id + effect_type` | 履约累计防重流水（出入库生效唯一计入） |
| `doc_relations` | `id`,`source_doc_type`,`source_doc_id`,`target_doc_type`,`target_doc_id`,`relation_type` | 同一关系去重唯一 | 单据上下游关系（支持一对多/多对多） |
| `doc_attachments` | `id`,`owner_doc_type`,`owner_doc_id`,`path`,`biz_tag` | 附件按业务归属冻结：合同附件挂合同，订单业务附件挂订单，付款凭证挂付款单，收款凭证挂收款单，发货指令单附件挂采购订单 | 凭证与业务附件 |
| `business_audit_logs` | `id`,`event_code`,`biz_type`,`biz_id`,`operator_id`,`before_json`,`after_json`,`occurred_at` | 关闭、终止、阈值阻断必须落审计日志 | 审计日志 |
| `system_configs` | `id`,`config_key`,`config_value`,`version`,`status` | 配置变更需版本化与审批留痕 | 参数中心 |
| `report_snapshots` | `id`,`report_code`,`snapshot_time`,`metric_payload`,`version` | 按版本存档，不覆盖历史口径 | 报表快照与口径追溯 |

## 3.2 通用审计字段（所有业务单据）
- 必填字段：`created_by`,`created_at`,`updated_by`,`updated_at`,`source_doc_id`,`source_event_id`,`biz_direction`。
- 状态变更字段：`approved_by`,`approved_at`,`confirmed_by`,`confirmed_at`,`terminated_by`,`terminated_at`,`terminate_reason`。
- 手工关闭专用：`manual_close_by`,`manual_close_at`,`manual_close_reason`,`manual_close_diff_amount`,`manual_close_diff_qty`。

## 3.3 关键计算口径冻结
- 数量履约（销售）：`contract_item.qty_out_acc = Σ已生效出库单数量（基于contract_qty_effects防重流水）`。
- 数量履约（采购）：`contract_item.qty_in_acc = Σ已生效入库单数量`。
- 金额闭环（销售）：`Σ(累计实际出库量 × 合同单价) = 销售合同累计实收净额`。
- 金额闭环（采购）：`Σ(累计实际入库量 × 合同单价) = 采购合同累计实付净额`。
- 保证金口径：保证金是收付款单业务类型，不另行加总，避免重复计入。
- 金额闭环容差：`abs(金额差额) <= 0.01` 视为闭环成立。
- 数量精度：数量计算、阈值校验、履约累计统一按 `0.001` 精度处理。
- 保证金净额伪代码（固定实现口径）：
```text
sales_receipt_net =
  SUM(receipt_docs.amount_actual where doc_type='NORMAL' and status in [已确认,已核销])
+ SUM(receipt_docs.amount_actual where doc_type='DEPOSIT' and status in [已确认,已核销] and refund_status != '已退款')
- SUM(receipt_docs.refund_amount where doc_type='DEPOSIT' and status in [已确认,已核销])

purchase_payment_net =
  SUM(payment_docs.amount_actual where doc_type='NORMAL' and status in [已确认,已核销])
+ SUM(payment_docs.amount_actual where doc_type='DEPOSIT' and status in [已确认,已核销] and refund_status != '已退款')
- SUM(payment_docs.refund_amount where doc_type='DEPOSIT' and status in [已确认,已核销])
```

## 3.4 状态枚举冻结
- 合同：`草稿` -> `待审批` -> `生效中` -> `数量履约完成` -> (`已关闭` 或 `手工关闭`) -> `已归档`；补充回退分支：`待审批 -> 草稿（驳回）`。
- 销售订单：`草稿` -> `待运营审批` -> `待财务审批` -> (`驳回` 或 `已衍生采购订单`) -> `执行中` -> `已完成`。
- 采购订单：`已创建` -> `待供应商确认` -> `供应商已确认` -> `待付款校验` -> `可继续执行` -> `执行中` -> `已完成`。
- 收付款单：首版冻结为 `草稿` -> `已确认` -> `已核销`；异常分支 `待补录金额`、`已终止`。`待审核/驳回` 独立接口不纳入首版。
- 出入库单：`草稿` -> `待提交` -> `已生效` -> `已过账`；异常分支 `校验失败`、`已终止`。
- 约束：合同状态进入`数量履约完成`后，新增出入库单一律不得生效。

## 4. 触发矩阵、幂等与补偿

## 4.1 触发矩阵

| 触发事件 | 前置条件 | 自动动作 | 幂等键 | 失败补偿 |
|---|---|---|---|---|
| 采购合同审批通过并生效 | 合同状态=`待审批` | 写入付款单（保证金）+ 入库单草稿的待处理任务，供下游模块消费生成实体单据 | `purchase_contract_effective:{contract_id}` | 重试3次，失败入补偿队列 |
| 销售合同审批通过并生效 | 合同状态=`待审批` | 写入收款单（保证金）的待处理任务，供下游模块消费生成实体单据 | `sales_contract_effective:{contract_id}` | 重试3次，失败告警+人工补录 |
| 销售订单财务审批通过 | 订单状态=`待财务审批` | 生成采购订单实体 + 付款单/收款单待处理任务，写入关系图 | `sales_order_finance_approved:{sales_order_id}` | 幂等重放；部分成功走反向补偿 |
| 销售衍生采购订单付款=0 | `source_sales_order_id`存在 | 无条件放行并标记`zero_pay_exception_flag=true` | `po_zero_pay_exception:{purchase_order_id}` | 放行后若补录失败，进入财务待办 |
| 付款单0金额提交（非规则11） | `amount_actual=0`且非销售衍生采购订单 | 按规则14执行阈值校验并决定放行/待补录 | `payment_zero_submit:{payment_doc_id}` | 不通过转`待补录金额` |
| 仓库正常流程出库确认 | 仓库执行完成 | 生成出库单待生效 | `warehouse_outbound_confirmed:{warehouse_ticket_id}` | 重试；失败转手工补录待办 |
| 手工补录出库单提交 | 绑定销售合同 | 进入阈值校验并生效/阻断 | `manual_outbound_submit:{outbound_doc_id}` | 阻断后保留`校验失败`可重提 |
| 出入库单生效履约累计 | 单据状态变更为`已生效` | 写入`contract_qty_effects`并更新`contract_items`累计值 | `qty_effect:{doc_type}:{doc_id}` | 唯一冲突则跳过重复累计并记录审计 |
| 合同已数量履约完成后的出入库提交 | 合同状态=`数量履约完成` | 阻断新增出入库单生效 | `contract_qty_done_block:{contract_id}:{doc_id}` | 返回阻断错误并写审计 |
| 入库单提交生效 | 录入实际入库量 | 执行超量阈值校验并生效/阻断 | `inbound_submit:{inbound_doc_id}` | 阻断后可调整数量重提 |
| 收款单0金额提交 | `amount_actual=0` | 按规则14执行阈值校验并决定放行/待补录 | `receipt_zero_submit:{receipt_doc_id}` | 不通过转`待补录金额` |
| 自动关闭校验任务 | 合同数量履约完成 | 按合同方向执行金额闭环校验 | `contract_auto_close_check:{contract_id}:{version}` | 校验失败转授权手工关闭 |
| 每日闭环扫描任务 | 每日定时触发 | 扫描`数量履约完成且未关闭`合同并生成看板告警 | `contract_close_scan:{date}:{contract_id}` | 重复触发幂等跳过，写审计 |
| 每日履约滞留扫描任务 | 每日定时触发 | 扫描`生效中且履约长时间未变化`合同并告警 | `contract_fulfillment_scan:{date}:{contract_id}` | 重复触发幂等跳过，写审计 |
| 手工关闭执行 | 授权通过+原因必填 | 锁定、终止未生效、释放预占、差异记录、归档 | `contract_manual_close:{contract_id}` | 任一步失败回滚本事务并告警 |

## 4.2 幂等规则冻结
- 所有自动触发写入`source_event_id`，重复事件仅返回已处理结果，不重复落库。
- 业务唯一冲突统一返回`HTTP 409`与业务错误码。
- 当前阶段按低并发假设，不引入分布式锁；通过幂等键 + 事务提交保证最终一致。
- 双通道防重：`doc_relations`关系唯一 + `contract_qty_effects`唯一累计流水双重保证，防止系统单与手工单重复计入履约量。

## 4.3 失败补偿规则冻结
- 同事务内失败：数据库回滚。
- 跨事务失败：记录`compensation_task`并异步重试。
- 重试上限：默认3次；超过上限进入人工待办并触发看板告警。

## 5. API 契约冻结（`/api/v1`）

## 5.1 合同域接口

| 接口 | 方法 | 关键请求字段 | 关键校验 | 关键响应 |
|---|---|---|---|---|
| `/contracts/purchase` | `POST` | `contract_no`,`supplier_id`,`items[]` | 油品明细必填；系统阈值参数已生效 | `contract_id`,`status=草稿` |
| `/contracts/sales` | `POST` | `contract_no`,`customer_id`,`items[]` | 油品明细必填；系统阈值参数已生效 | `contract_id`,`status=草稿` |
| `/contracts/{id}/submit` | `POST` | `comment` | 状态必须是`草稿` | `status=待审批` |
| `/contracts/{id}/approve` | `POST` | `approval_result`,`comment` | 状态必须是`待审批` | `approval_result=true` 返回 `status=生效中`；`approval_result=false` 返回 `status=草稿` |
| `/contracts/{id}` | `GET` | 无 | 仅授权角色可读 | 合同头、明细、阈值快照、状态 |
| `/contracts/{id}/manual-close` | `POST` | `reason`,`confirm_token` | 原因必填；权限校验；二次确认 | `status=手工关闭` |
| `/contracts/{id}/graph` | `GET` | 无 | 仅授权角色可读 | 合同节点 + 当前待处理下游任务 + 已形成关系图谱 |

## 5.2 订单域接口

| 接口 | 方法 | 关键请求字段 | 关键校验 | 关键响应 |
|---|---|---|---|---|
| `/sales-orders` | `POST` | `sales_contract_id`,`oil_product_id`,`qty`,`unit_price` | `unit_price`必须等于合同单价 | `sales_order_id`,`status` |
| `/sales-orders/{id}` | `PUT` | `oil_product_id`,`qty`,`unit_price` | 仅允许 `草稿/驳回`；驳回态保存后自动回 `草稿` | `status`,`message` |
| `/sales-orders/{id}/submit` | `POST` | `comment` | 状态必须是`草稿` | `status=待运营审批` |
| `/sales-orders/{id}/ops-approve` | `POST` | `result`,`comment` | 状态必须是`待运营审批` | 新状态 |
| `/sales-orders/{id}/finance-approve` | `POST` | `result`,`purchase_contract_id`,`actual_receipt_amount`,`actual_pay_amount`,`comment` | 财务通过时必须绑定已生效采购合同；通过后触发采购订单 + 收付款任务 | 采购订单编号 + 收付款待处理任务 |
| `/purchase-orders/{id}` | `GET` | 无 | 权限校验 | 采购订单详情 |

## 5.3 资金单据接口

| 接口 | 方法 | 关键请求字段 | 关键校验 | 关键响应 |
|---|---|---|---|---|
| `/receipt-docs/{id}/confirm` | `POST` | `amount_actual`,`voucher_files[]` | 非0金额必须有凭证；0金额按规则14校验 | `status=已确认`或`待补录金额` |
| `/payment-docs/{id}/confirm` | `POST` | `amount_actual`,`voucher_files[]` | 非0金额必须有凭证；0金额在规则11场景无条件放行，其他场景按规则14校验 | `status=已确认`或`待补录金额` |

- 规则14实现口径冻结补充：
  - 仅适用于“订单衍生的普通收款单/付款单”，不适用于合同保证金单据。
  - 保证金对应数量 = `已确认/已核销且未退款的保证金净额 / 当前订单油品对应合同单价`
  - 待执行数量：
    - 销售方向：`contract_item.qty_signed - contract_item.qty_out_acc`
    - 采购方向：`contract_item.qty_signed - contract_item.qty_in_acc`
| `/payment-docs/supplement` | `POST` | `contract_id`,`purchase_order_id`,`amount_actual` | 手工补录必须同时绑定合同+采购订单 | `payment_doc_id` |
| `/receipt-docs/supplement` | `POST` | `contract_id`,`sales_order_id`,`amount_actual` | 手工补录必须绑定合同 | `receipt_doc_id` |

## 5.4 仓储执行接口

| 接口 | 方法 | 关键请求字段 | 关键校验 | 关键响应 |
|---|---|---|---|---|
| `/inbound-docs/{id}/submit` | `POST` | `actual_qty`,`warehouse_id` | 超量阈值校验；合同数量履约完成阻断；失败转`校验失败` | `status` |
| `/outbound-docs/{id}/submit` | `POST` | `actual_qty`,`warehouse_id` | 超量阈值校验；合同数量履约完成阻断；失败转`校验失败` | `status` |
| `/outbound-docs/warehouse-confirm` | `POST` | `contract_id`,`sales_order_id`,`source_ticket_no`,`actual_qty`,`warehouse_id` | 必须绑定销售合同+销售订单；销售订单状态必须为`已衍生采购订单/执行中`；`source_ticket_no`参与幂等去重 | `outbound_doc_id`,`status=待提交` |
| `/outbound-docs/manual` | `POST` | `contract_id`,`oil_product_id`,`sales_order_id`,`manual_ref_no`,`actual_qty`,`reason` | 必须绑定销售合同+销售订单；销售订单状态必须为`已衍生采购订单/执行中`；`manual_ref_no`在合同+油品下唯一 | `outbound_doc_id` |

## 5.5 看板与报表接口

| 接口 | 方法 | 说明 | SLA |
|---|---|---|---|
| `/dashboard/summary` | `GET` | 管理后台仪表盘四项核心指标 | `T+0`（5分钟内） |
| `/boards/tasks` | `GET` | 待办、阻塞、超阈值告警 | `T+0` |
| `/reports/light/overview` | `GET` | 小程序轻量汇总报表 | `T+0` |
| `/reports/admin/multi-dim` | `GET` | 后台多维管理报表 | `T+0~T+1` |

## 5.6 参数中心接口（系统级阈值）

| 接口 | 方法 | 关键请求字段 | 关键校验 | 关键响应 |
|---|---|---|---|---|
| `/system-configs/thresholds` | `GET` | 无 | 权限校验（管理员） | `threshold_release`,`threshold_over_exec`,`version` |
| `/system-configs/thresholds` | `PUT` | `threshold_release`,`threshold_over_exec`,`reason` | `threshold_release <= threshold_over_exec`；版本化留痕 | `status=生效`,`version` |

## 5.7 错误码冻结

| 错误码 | 触发场景 | 说明 |
|---|---|---|
| `BIZ-CONTRACT-THRESHOLD-001` | 出入库超量履约阈值 | 阻断单据生效 |
| `BIZ-RECEIPT-ZERO-001` | 收款0金额不满足规则14阈值 | 转`待补录金额` |
| `BIZ-PAY-ZERO-001` | 付款0金额不满足规则11/规则14放行条件 | 转`待补录金额` |
| `BIZ-LINK-001` | 上下游ID缺失或关系不完整 | 阻断审核/生效 |
| `BIZ-CLOSE-001` | 合同方向金额闭环不满足（超出0.01容差） | 不允许自动关闭 |
| `BIZ-CONTRACT-QTY-DONE-001` | 合同已数量履约完成仍尝试新增出入库生效 | 阻断提交 |
| `BIZ-QTY-DEDUP-001` | 双通道履约累计命中重复键 | 跳过重复累计并记录审计 |
| `BIZ-PAY-SUPPLEMENT-001` | 手工补录付款单缺合同或采购订单 | 阻断提交 |
| `BIZ-ORDER-PRICE-001` | 订单单价与合同单价不一致 | 阻断提交 |

## 6. 原型冻结包（页面/字段/动作）

## 6.1 页面冻结清单
- 管理后台：`ADM-DASH-01`、`ADM-BOARD-01`、`ADM-CONTRACT-*`、`ADM-ORDER-*`、`ADM-PAYMENT-01`、`ADM-RECEIPT-01`、`ADM-INBOUND-01`、`ADM-OUTBOUND-01`、`ADM-TRACE-01`、`ADM-AUDIT-01`、`ADM-CONFIG-01`。
- 小程序：`MINI-TODO-01`、`MINI-ORDER-01`、`MINI-EXEC-01`、`MINI-INOUT-01`、`MINI-REPORT-01`、`MINI-MSG-01`。

## 6.2 关键字段字典冻结
- 合同：编号、方向、油品、签约数量、单价、系统阈值快照、状态。
- 订单：来源合同、油品、数量、合同单价、实收实付、状态。
- 收付款单：业务类型、金额、凭证要求、免凭证原因、核销状态。
- 出入库单：来源类型（系统/手工）、实际数量、仓库、阈值校验结果、过账状态。
- 图谱：来源单据、目标单据、关系类型、触发事件ID。

## 6.3 交互动作字典冻结
- `提交`：仅当必填字段与业务校验通过可执行。
- `审核通过`：写入审批人与时间并触发下游自动动作。
- `驳回`：写入驳回原因（仅管理后台支持执行驳回）。
- `确认收付款`：执行凭证校验与金额校验，更新资金台账。
- `生效出入库`：执行超量阈值校验，通过后过账。
- `手工关闭`：执行五步处理顺序并写入差异记录。

## 6.4 视觉与文案冻结（关键）
- 采购订单0付款例外统一文案：`例外放行（需后补付款单）`。
- 仪表盘首版四项核心指标固定，不在首版页面增减。
- 小程序仅展示审批驳回结果，不提供驳回动作入口。
- 管理后台与小程序所有用户可见文案统一中文：系统提示、流程阻断提示、字段标签、状态描述、按钮文案、消息通知、空态与异常态提示均需中文显示。
- API返回可保留英文错误码`code`，但对用户可见的错误消息`message`必须为中文，不得直接透传英文异常。

## 7. 报表实现策略冻结
- 采用“事件触发增量更新 + 定时全量校准”混合模式。
- 事件源：合同生效、订单审批、收付款确认、出入库生效、手工关闭。
- 口径版本：报表查询必须带`metric_version`，默认返回当前生效版本。
- 重算策略：仅对口径变更涉及范围执行重算并保留旧版本快照。
- 定时任务：每日执行合同闭环扫描与履约滞留扫描，任务幂等键防重复触发，任务结果落审计并推送看板告警。

## 8. 阶段B出口门槛
- 数据模型、触发矩阵、API契约、原型冻结包完成联合评审。
- 业务、财务、仓储、前后端、测试五方签字通过。
- 阶段C开发前，不再接受跨模块口径改动；变更走版本流程。

## 9. 阶段C实施入口（不开发）
1. 按`M1~M8`模块顺序拆解开发任务。
2. 每个子模块必须先落测试用例清单，再进入编码。
3. 每迭代完成后执行：自检 -> 联调 -> 回归 -> 文档更新 -> 提交推送。
