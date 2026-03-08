# JGPort V6 重建工作区

## 1. 当前状态
- 本仓库已切换到 **V6 重建模式**。
- 历史 V5 代码与文档已归档至 `archive/v5/`，用于追溯与参考，不再作为 V6 默认开发目录。
- V6 默认开发目录：`backend/`、`admin-web/`、`miniprogram/`、`docs/`。
- 旧版主链已完成：`M1~M7` 后端与报表首批能力，`M8-01 ~ M8-28` 管理后台、小程序、报表、导出、重算等首批能力均已落地，并形成旧版“可联调”基线。
- 当前项目目标已纠偏为：以“生产可用版本”为唯一交付目标，先完成 `docs/V6生产可用版本治理总纲.md`、`docs/V6阶段E-验收发布与上线清单.md`、`docs/V6规则-实现-测试-验收追踪矩阵.md` 三份宏观基线，再按 `G1 前置治理基座 -> G2 正式身份与端收口 -> G3 订单后半状态机闭环 -> G4 真实业务全链路回归 -> G5 发布与上线准备` 顺序推进。

## 2. 目录说明
- `backend/`：V6 后端工程（FastAPI + PostgreSQL 18）
- `admin-web/`：V6 管理后台工程（Vue 3 + Element Plus，工程组织对齐 Vben Admin）
- `miniprogram/`：V6 小程序执行链工程
- `docs/`：V6 文档目录，现行基线见 `docs/README.md`，历史任务包归档在 `docs/history/`
- `archive/v5/`：V5 归档区（只读参考，避免干扰 V6 开发）

## 3. 启动建议
1. 先启动 V6 后端并完成 PostgreSQL 迁移验证。
2. 再启动 V6 管理后台并对接 `/api/v1`。
3. 小程序当前已完成登录入口、待办入口、消息中心、客户订单页、轻量报表页、仓库执行回执页、供应商采购进度页、供应商附件回传、单笔发货确认与付款校验结果回看首批能力、消息来源页回看与深链一致性首批能力、开发者工具本地联调模式与微信登录骨架，可在微信开发者工具中切换演示模式、本地联调或微信登录模式；其中真实微信登录链路仍属于“已有骨架、待在 `G2` 阶段完成正式收口”的状态。

## 4. 说明
- 已完成 V6 后端基座初始化（FastAPI + Alembic + PostgreSQL）。
- 当前已验证 `alembic upgrade head`、`pytest`、`/api/v1/healthz` 可用。

## 5. V6 后端快速启动
```bash
cd backend
conda activate jgport
cp .env.example .env
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
