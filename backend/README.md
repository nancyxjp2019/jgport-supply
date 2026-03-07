# V6 后端工程

## 1. 当前状态
- 已完成最小可运行基座初始化：`FastAPI + SQLAlchemy + Alembic + PostgreSQL`。
- 已提供健康检查接口：`GET /api/v1/healthz`。
- 已提供迁移版本：
  - `0001_init_v6_schema`（基础 `business_logs` 表）
  - `0002_add_m1_foundation`（M1：权限边界、阈值版本、审计日志基座）
  - `0003_fix_m1_review_findings`（M1：修复鉴权、版本化与测试隔离问题）
  - `0004_add_m2_contract_domain`（M2：合同主表、明细表、合同生效待处理任务）
  - `0005_add_m3_order_domain`（M3：销售订单、采购订单、销售订单衍生任务）
  - `0006_add_m4_funds_domain`（M4：收款单、付款单、单据关系表）
  - `0007_add_m4_doc_attach`（M4：凭证附件表）
  - `0008_add_m5_inventory_exec`（M5：入库单、出库单、履约累计防重表）
  - `0009_add_m6_contract_close`（M6：合同关闭字段、手工关闭差异记录）
  - `0010_add_m7_reports`（M7：仪表盘、看板、轻量报表快照）
  - `0011_add_m8_wechat_auth`（M8-06：小程序微信登录绑定表）
  - `0012_m8_supplier_confirm`（M8-14：供应商发货确认留痕字段）

## 2. 目录说明
- `app/main.py`：应用入口
- `app/core/config.py`：配置加载
- `app/db/`：数据库连接与基础模型
- `app/models/business_log.py`：审计日志模型
- `app/models/role_company_binding.py`：角色-公司绑定模型
- `app/models/threshold_config_version.py`：双阈值版本模型
- `app/models/business_audit_log.py`：结构化审计日志模型
- `app/models/contract.py`：合同主表模型
- `app/models/contract_item.py`：合同油品明细模型
- `app/models/contract_effective_task.py`：合同生效待处理任务模型
- `alembic/`：迁移脚本
- `tests/`：健康检查 + M1/M2/M3/M4/M5/M6/M7 接口与服务测试
- `app/models/report_snapshot.py`：报表快照模型
- `app/services/report_service.py`：仪表盘、业务看板、轻量报表服务

## 3. 已实现接口（阶段C迭代1-M1）
- 健康检查：
  - `GET /api/v1/healthz`
- 端权限边界：
  - `GET /api/v1/access/me`
  - `POST /api/v1/access/check`
- 参数中心（双阈值）：
  - `GET /api/v1/system-configs/thresholds`
  - `PUT /api/v1/system-configs/thresholds`
- 审计日志：
  - `POST /api/v1/audit/logs`
  - `GET /api/v1/audit/logs`

## 4. 已实现接口（阶段C迭代2-M2）
- 合同域：
  - `POST /api/v1/contracts/purchase`
  - `POST /api/v1/contracts/sales`
  - `POST /api/v1/contracts/{id}/submit`
  - `POST /api/v1/contracts/{id}/approve`
  - `POST /api/v1/contracts/{id}/manual-close`
  - `GET /api/v1/contracts/{id}`
  - `GET /api/v1/contracts/{id}/graph`
- 当前实现约束：
  - 合同早期状态流转已落地：`草稿 -> 待审批 -> 生效中`，驳回回退 `草稿`。
  - 审批通过时写入阈值快照。
  - 审批通过时先写入 `contract_effective_tasks`，由后续 M4/M5 消费生成收付款单、入库单等实体单据。
  - 请求参数校验失败统一返回中文 `message/detail`，避免终端直接暴露英文校验提示。

## 5. 受保护接口身份上下文
- 当前阶段受保护接口采用服务端身份上下文校验，调用方需透传以下请求头：
  - `X-User-Id`
  - `X-Role-Code`
  - `X-Company-Id`
  - `X-Company-Type`
  - `X-Client-Type`
  - `X-Auth-Secret`
- 上述身份上下文应由网关、登录中间层或服务端代理透传，不应由终端页面直接拼装。
- `X-Auth-Secret` 必须与环境变量 `auth_proxy_shared_secret` 一致。
- 非开发环境必须显式配置随机密钥，禁止继续使用默认开发密钥。
- 开发者工具本地联调另提供 `Authorization: Bearer <token>` 方式，仅 `dev/test` 环境开放，由 `POST /api/v1/mini-auth/dev-login` 签发，不能替代正式登录体系。
- 小程序正式微信登录也使用 `Authorization: Bearer <token>` 访问受保护接口；非开发环境必须显式配置 `direct_auth_token_secret`。
- `GET/PUT /api/v1/system-configs/thresholds` 仅允许 `admin + operator_company + admin_web`。
- `GET /api/v1/audit/logs` 允许 `admin/finance/operations + operator_company + admin_web`。
- `POST /api/v1/audit/logs` 仅允许 `admin + operator_company + admin_web`。
- `POST /api/v1/contracts/*` 与 `POST /api/v1/contracts/{id}/approve` 仅允许 `finance/admin + operator_company + admin_web`。
- `POST /api/v1/contracts/{id}/manual-close` 仅允许 `finance/admin + operator_company + admin_web`。
- `GET /api/v1/contracts/{id}` 与 `GET /api/v1/contracts/{id}/graph` 允许 `operations/finance/admin + operator_company + admin_web`。
- `GET /api/v1/sales-contracts/available` 仅允许 `customer + customer_company + miniprogram`，且必须透传所属 `X-Company-Id`。
- `GET /api/v1/sales-orders` 允许：
  - `customer + customer_company + miniprogram`，且必须透传所属 `X-Company-Id`；
  - `operations/finance/admin + operator_company + admin_web`。
- `GET /api/v1/sales-orders/{id}` 允许：
  - `customer + customer_company + miniprogram`，且仅可读取本公司订单；
  - `operations/finance/admin + operator_company + admin_web`。
- `PUT /api/v1/sales-orders/{id}` 允许：
  - `customer + customer_company + miniprogram`，且必须透传所属 `X-Company-Id`；
  - `operations/finance/admin + operator_company + admin_web`。
- `POST /api/v1/sales-orders` 与 `POST /api/v1/sales-orders/{id}/submit` 允许：
  - `customer + customer_company + miniprogram`，且必须透传所属 `X-Company-Id`；
  - `operations/finance/admin + operator_company + admin_web`。
- `POST /api/v1/sales-orders/{id}/ops-approve` 仅允许 `operations/admin + operator_company + admin_web`。
- `POST /api/v1/sales-orders/{id}/finance-approve` 仅允许 `finance/admin + operator_company + admin_web`。
- `GET /api/v1/purchase-orders/{id}` 允许 `operations/finance/admin + operator_company + admin_web`。
- `POST /api/v1/supplier/purchase-orders/{id}/confirm-delivery` 仅允许 `supplier + supplier_company + miniprogram`，且仅可确认本公司名下、状态为 `待供应商确认` 的采购订单。
- `POST /api/v1/payment-docs/supplement` 仅允许 `finance/admin + operator_company + admin_web`。
- `POST /api/v1/receipt-docs/supplement` 仅允许 `finance/admin + operator_company + admin_web`。
- `POST /api/v1/payment-docs/{id}/confirm` 仅允许 `finance/admin + operator_company + admin_web`。
- `POST /api/v1/receipt-docs/{id}/confirm` 仅允许 `finance/admin + operator_company + admin_web`。
- `POST /api/v1/inbound-docs/{id}/submit` 允许：
  - `warehouse + warehouse_company + miniprogram`；
  - `operations/finance/admin + operator_company + admin_web`。
- `POST /api/v1/outbound-docs/warehouse-confirm` 允许：
  - `warehouse + warehouse_company + miniprogram`；
  - `operations/finance/admin + operator_company + admin_web`。
- `POST /api/v1/outbound-docs/manual` 允许：
  - `warehouse + warehouse_company + miniprogram`；
  - `operations/finance/admin + operator_company + admin_web`。
- `POST /api/v1/outbound-docs/{id}/submit` 允许：
  - `warehouse + warehouse_company + miniprogram`；
  - `operations/finance/admin + operator_company + admin_web`。
- `GET /api/v1/dashboard/summary` 仅允许 `operations/finance/admin + operator_company + admin_web`。
- `GET /api/v1/boards/tasks` 仅允许 `operations/finance/admin + operator_company + admin_web`。
- `GET /api/v1/reports/light/overview` 仅允许 `operations/finance/admin + operator_company + miniprogram`。
- `GET /api/v1/reports/admin/multi-dim` 仅允许 `operations/finance/admin + operator_company + admin_web`，当前返回 `501` 表示尚未纳入首批实现。

## 6. 已实现接口（阶段C迭代3-M3）
- 订单域：
  - `GET /api/v1/sales-contracts/available`
  - `GET /api/v1/sales-orders`
  - `GET /api/v1/sales-orders/{id}`
  - `POST /api/v1/sales-orders`
  - `PUT /api/v1/sales-orders/{id}`
  - `POST /api/v1/sales-orders/{id}/submit`
  - `POST /api/v1/sales-orders/{id}/ops-approve`
  - `POST /api/v1/sales-orders/{id}/finance-approve`
  - `GET /api/v1/purchase-orders/{id}`
- 当前实现约束：
  - 销售订单状态流转已落地：`草稿 -> 待运营审批 -> 待财务审批 -> （驳回 或 已衍生采购订单）`。
  - 销售订单处于 `驳回` 时，保存修改后自动回到 `草稿`。
  - 财务审批通过时必须绑定已生效采购合同。
  - 财务审批通过后，本轮只生成采购订单实体，并写入 `sales_order_derivative_tasks` 供 M4 消费生成收付款单。
  - 销售衍生采购订单 `付款金额=0` 时，仅设置 `zero_pay_exception_flag=true`，不豁免采购合同绑定。

## 7. 本地启动
```bash
cd backend
conda activate jgport
cp .env.example .env
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问地址：`http://127.0.0.1:8000/api/v1/healthz`

## 8. 说明
- V5 后端代码已归档至 `archive/v5/backend/`，仅供对照。
- 若 `psql` 未在 PATH，可使用完整路径执行，例如：`/usr/local/Cellar/postgresql@18/18.3/bin/psql`。
- 测试默认使用临时 PostgreSQL 数据库，测试结束后自动销毁，不污染开发库。
- `POST /api/v1/mini-auth/dev-login` 仅用于微信开发者工具本地联调；非开发环境不得作为正式认证方案。

## 9. 已实现接口（阶段C迭代4-M4）
- 资金单据：
  - `POST /api/v1/payment-docs/supplement`
  - `POST /api/v1/receipt-docs/supplement`
  - `POST /api/v1/payment-docs/{id}/confirm`
  - `POST /api/v1/receipt-docs/{id}/confirm`
- 当前实现约束：
  - 采购合同/销售合同生效后，会同步消费待处理任务并生成保证金收付款单草稿。
  - 销售订单财务审批通过后，会同步消费待处理任务并生成订单实收实付收付款单草稿。
  - `付款金额=0` 的销售衍生采购订单，会生成带“例外放行（需后补付款单）”文案的付款单草稿。
  - 手工补录付款单必须绑定匹配的 `采购合同 + 采购订单`。
  - 手工补录收款单必须绑定匹配的 `销售合同 + 销售订单`。
  - 非0金额确认必须上传凭证路径，并落库到 `doc_attachments`。
  - `付款金额=0` 且命中规则11时无条件放行并可免凭证。
  - `收款金额=0` 或非规则11的 `付款金额=0` 时，按规则14计算后转 `已确认` 或 `待补录金额`。
  - 已转 `待补录金额` 的单据，可继续调用原确认接口补录金额和凭证后再次确认。
  - 当前仍未实现退款/核销、收付款单驳回/待审核独立接口和真实文件上传。

## 10. 已实现接口（阶段C迭代5-M5）
- 仓储执行：
  - `POST /api/v1/inbound-docs/{id}/submit`
  - `POST /api/v1/outbound-docs/warehouse-confirm`
  - `POST /api/v1/outbound-docs/manual`
  - `POST /api/v1/outbound-docs/{id}/submit`
- 当前实现约束：
  - 采购合同审批生效后，会按合同油品明细自动生成入库单草稿。
  - 仓库正常流程出库必须绑定销售合同、销售订单、仓库回执号，并按回执号幂等去重。
  - 手工补录出库必须绑定 `销售合同 + 销售订单 + 油品`，且手工回执号在合同+油品维度唯一。
  - 所有出库单只能基于状态为 `已衍生采购订单` 或 `执行中` 的销售订单生成，不能绕过审批主链。
  - 出入库提交会执行合同超量履约阈值校验；超限转 `校验失败`，合同已数量履约完成则转 `已终止`。
  - 过账成功后写入 `contract_qty_effects` 防重流水，并累计到 `contract_items.qty_in_acc/qty_out_acc`。
  - 当合同全部油品明细达到签约数量时，合同状态自动更新为 `数量履约完成`。
  - 当前仍未实现独立库存台账、库存余额报表、订单完成态联动与供应商确认发货状态机。

## 11. 已实现接口（阶段C迭代6-M6）
- 合同关闭：
  - `POST /api/v1/contracts/{id}/manual-close`
- 当前实现约束：
  - 金额闭环按合同方向分开计算：销售只看收款净额，采购只看付款净额。
  - 当合同已达到 `数量履约完成` 且金额闭环满足 `|差额| <= 0.01` 时，会在收付款确认或出入库过账后自动关闭合同。
  - 自动关闭与手工关闭都会执行关闭收口：未终态的收付款单、入库单、出库单统一转 `已终止` 并写审计。
  - 手工关闭要求：合同已达到 `数量履约完成`、原因必填、确认口令固定为 `MANUAL_CLOSE`。
  - 手工关闭会记录关闭差异金额与按油品的关闭差异数量明细。
  - 合同进入 `已关闭/手工关闭` 后，资金补录、出入库补录、出入库再次提交与后续资金确认会被服务端阻断。
  - 当前仍未实现每日闭环扫描任务、看板告警、合同 `已归档` 状态与订单完成态联动。

## 12. 已实现接口（阶段C迭代7-M7首批）
- 报表与看板：
  - `GET /api/v1/dashboard/summary`
  - `GET /api/v1/boards/tasks`
  - `GET /api/v1/reports/light/overview`
  - `GET /api/v1/reports/admin/multi-dim`（占位返回 `501`）
- 当前实现约束：
  - 仪表盘首版四指标已按规则41固定：合同执行率、当日实收实付、库存周转、超阈值告警数。
  - 合同执行率仅统计 `生效中/数量履约完成/已关闭/手工关闭/已归档` 合同。
  - 报表“当日”口径统一按 `Asia/Shanghai` 自然日计算。
  - 小程序轻量报表首版仅向运营侧角色开放，不向客户/供应商/仓库暴露经营金额汇总。
  - 查询报表时会写入 `report_snapshots` 快照，版本固定为 `v1`，历史快照不覆盖。
  - 当前仍未实现多维管理报表、每日扫描任务、事件触发增量刷新编排与报表导出。

## 13. 已实现接口（阶段C迭代8-M8-05）
- 小程序开发者工具本地联调：
  - `POST /api/v1/mini-auth/dev-login`
- 当前实现约束：
  - 仅 `dev/test` 环境开放本地联调令牌签发。
  - `POST /api/v1/mini-auth/dev-login` 会根据冻结角色与公司归属返回 `Bearer` 令牌。
  - 受保护接口在 `dev/test` 环境支持 `Authorization: Bearer <token>` 本地联调方式。
  - 该链路仅用于微信开发者工具本地联调，不能替代正式微信登录与生产认证。

## 14. 已实现接口（阶段C迭代8-M8-06）
- 小程序微信登录：
  - `POST /api/v1/mini-auth/wechat-login`
- 当前实现约束：
  - 服务端通过微信官方 `code2session` 接口完成 `openid/session_key` 交换。
  - 若微信账号已绑定业务角色，则签发 Bearer 令牌并返回当前角色与公司归属。
  - 若微信账号未绑定业务角色，则返回 `binding_required=true`；在 `dev/test` 环境附带 `debug_openid` 供本地绑定脚本使用。
  - 当前仓库提供绑定脚本：`cd backend && python scripts/bootstrap_mini_program_account.py --openid ... --role-code ... --company-id ... --company-type ...`。
  - 本轮只完成微信登录骨架，不包含后台绑定 UI、真机 HTTPS 联调与正式用户中心。

## 15. 已实现接口（阶段C迭代8-M8-08）
- 小程序客户订单首批：
  - `GET /api/v1/sales-contracts/available`
  - `GET /api/v1/sales-orders`
  - `GET /api/v1/sales-orders/{id}`
- 当前实现约束：
  - 可选合同查询仅返回当前客户公司下状态为 `生效中` 的销售合同及油品明细。
  - 客户只能查询本公司订单；运营、财务、管理员可在管理后台读取订单列表与详情。
  - 订单列表支持 `status` 状态筛选与 `limit` 条数限制，默认按 `id DESC` 返回。
  - 返回结果补充 `sales_contract_no` 与 `created_at`，用于小程序订单页展示与继续编辑。
  - 本轮只补查询接口，不新增小程序审批动作、附件上传与采购订单详情页。
