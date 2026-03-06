# V6 后端工程

## 1. 当前状态
- 已完成最小可运行基座初始化：`FastAPI + SQLAlchemy + Alembic + PostgreSQL`。
- 已提供健康检查接口：`GET /api/v1/healthz`。
- 已提供迁移版本：
  - `0001_init_v6_schema`（基础 `business_logs` 表）
  - `0002_add_m1_foundation`（M1：权限边界、阈值版本、审计日志基座）
  - `0003_fix_m1_review_findings`（M1：修复鉴权、版本化与测试隔离问题）
  - `0004_add_m2_contract_domain`（M2：合同主表、明细表、合同生效待处理任务）

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
- `tests/`：健康检查 + M1/M2 接口与服务测试

## 3. 已实现接口（阶段C迭代1-M1）
- 健康检查：
  - `GET /api/v1/healthz`
- 端权限边界：
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
  - `X-Company-Type`
  - `X-Client-Type`
  - `X-Auth-Secret`
- 上述身份上下文应由网关、登录中间层或服务端代理透传，不应由终端页面直接拼装。
- `X-Auth-Secret` 必须与环境变量 `auth_proxy_shared_secret` 一致。
- `GET/PUT /api/v1/system-configs/thresholds` 仅允许 `admin + operator_company + admin_web`。
- `GET /api/v1/audit/logs` 允许 `admin/finance/operations + operator_company + admin_web`。
- `POST /api/v1/audit/logs` 仅允许 `admin + operator_company + admin_web`。
- `POST /api/v1/contracts/*` 与 `POST /api/v1/contracts/{id}/approve` 仅允许 `finance/admin + operator_company + admin_web`。
- `GET /api/v1/contracts/{id}` 与 `GET /api/v1/contracts/{id}/graph` 允许 `operations/finance/admin + operator_company + admin_web`。

## 6. 本地启动
```bash
cd backend
conda activate jgport
cp .env.example .env
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问地址：`http://127.0.0.1:8000/api/v1/healthz`

## 7. 说明
- V5 后端代码已归档至 `archive/v5/backend/`，仅供对照。
- 若 `psql` 未在 PATH，可使用完整路径执行，例如：`/usr/local/Cellar/postgresql@18/18.3/bin/psql`。
- 测试默认使用临时 PostgreSQL 数据库，测试结束后自动销毁，不污染开发库。
