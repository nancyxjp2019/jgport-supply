# 新项目重建基座说明（Vue 3 + Element Plus + Vben Admin + PostgreSQL）

## 1. 目标与范围
- 目标：基于当前 V5 业务内核重建新项目，替换后台前端技术实现，并将数据库主引擎切换为 PostgreSQL（推荐版本 18）。
- 范围：
  - 保留业务规则与状态机口径；
  - 保留后端业务域代码与 API；
  - 重建后台前端为 `Vue 3 + Element Plus + Vben Admin`；
  - 新项目开发 Python 环境统一为 Conda `jgport`；
  - 不迁移 UAT 相关代码（文档中的历史 UAT 章节仅作归档参考，不作为实现基线）。

## 2. 技术栈变化影响评估

### 2.1 后台前端改造（Vben）
- 需要变更：
  - 旧后台静态页 `backend/app/web/admin_console` 不再作为主实现。
  - 新增独立前端工程（建议目录：`admin-web/`），通过 API 调用后端。
  - 菜单、路由、权限按钮、字段字典转为前端工程内模块化维护。
- 保持不变：
  - 权限最终校验仍以后端 `require_roles` 与服务层校验为准。
  - 订单终止、库存扣减、合同状态流转仍由后端事务控制。

### 2.2 数据库切换（PostgreSQL）
- 需要变更：
  - 数据库版本基线固定为 PostgreSQL 18（截至 2026-03-05 的最新主版本）。
  - `database_url` 默认值改为 PostgreSQL DSN。
  - 驱动依赖由 `PyMySQL` 迁移到 `psycopg[binary]`。
  - 新项目初始化后执行一次完整迁移（`alembic upgrade head`）。
- 影响关注：
  - `Numeric`、时间时区、唯一索引与大小写比较策略需按 PostgreSQL 校验。
  - 报表 SQL 与分页排序在 PostgreSQL 下做一次性能回归。

### 2.3 微信小程序处理
- 建议策略：
  - 小程序业务代码可作为“执行链参考基座”迁入新仓；
  - 清理 UAT 运行器与测试桥接逻辑；
  - 后续按新 API 契约逐页重构（建单、详情、报表、合同中心）。

## 3. 新项目基座目录（当前状态）
- 根目录：`jgport`（当前仓库）
- 结构：
  - `docs/`：核心业务、接口、状态机、安全、部署文档（保留少量历史 UAT 章节用于追溯）
  - `backend/`：后端业务内核代码、迁移脚本、核心初始化脚本
  - `admin-web/`：后台前端工程，已基于 `Vben Admin v5.6.0` 初始化（包含 `web-ele` 方案）
  - `miniprogram/`：小程序执行链代码基座（已排除 UAT 运行器）

### 3.1 admin-web 安装与启动
```bash
cd admin-web
corepack enable
corepack pnpm install
corepack pnpm run dev:ele --host 0.0.0.0 --port 5666
```

默认访问：`http://127.0.0.1:5666`

## 4. 执行优先级建议
1. 创建并激活 Conda 环境 `jgport`，固化 PostgreSQL 18 环境并跑通后端迁移。
2. 生成并冻结 OpenAPI 契约，作为 Vben 与小程序联调基线。
3. 优先迁移后台核心页面：销售订单、采购订单、合同、采购入库、库存。
4. 最后迁移报表中心与审计查询页面。

## 5. 合规与审计要求（重建过程必须保留）
- 所有终止类动作必须保留“原因必填 + 二次确认 + 审计日志”。
- 关键状态变化必须持续写入 `business_logs`。
- 合同、订单、库存三大域的跨对象联动必须维持同事务落库。
