# 后端服务（新项目基座）

## 1. 运行环境
- Conda 环境：`jgport`
- Python 3.11+
- PostgreSQL 18（推荐；截至 2026-03-05 为最新主版本）

## 2. 本地启动
```bash
cd backend
conda activate jgport
cp .env.example .env
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问：`http://127.0.0.1:8000/docs`

## 3. 数据库与迁移
```bash
cd backend
alembic upgrade head
```

常用命令：
```bash
alembic revision --autogenerate -m "your_migration_message"
alembic upgrade head
alembic downgrade -1
```

## 4. 账号初始化脚本
```bash
cd backend
python -m scripts.bootstrap_admin --username admin --display-name "系统管理员"
python -m scripts.bootstrap_super_admin --username root --display-name "超级管理员" --password "请替换为强密码"
python -m scripts.generate_totp_qr --totp-uri "粘贴上一步输出的 totp_uri"
```

## 5. API 范围（V5）
- 健康检查、认证、用户与主数据
- 销售订单、采购订单
- 销售合同、采购合同
- 采购入库、库存调整、库存台账
- 报表中心、业务日志

## 6. 说明
- 本基座不包含 UAT 路由与 UAT 自动化脚本。
- 管理后台前端将由独立 `admin-web` 工程承载（Vue 3 + Element Plus + Vben Admin）。
