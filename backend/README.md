# V6 后端工程

## 1. 当前状态
- 已完成最小可运行基座初始化：`FastAPI + SQLAlchemy + Alembic + PostgreSQL`。
- 已提供健康检查接口：`GET /api/v1/healthz`。
- 已提供首个迁移版本：`0001_init_v6_schema`（包含 `business_logs` 表）。

## 2. 目录说明
- `app/main.py`：应用入口
- `app/core/config.py`：配置加载
- `app/db/`：数据库连接与基础模型
- `app/models/business_log.py`：审计日志模型
- `alembic/`：迁移脚本
- `tests/test_health.py`：基础健康检查测试

## 3. 本地启动
```bash
cd backend
conda activate jgport
cp .env.example .env
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问地址：`http://127.0.0.1:8000/api/v1/healthz`

## 4. 说明
- V5 后端代码已归档至 `archive/v5/backend/`，仅供对照。
- 若 `psql` 未在 PATH，可使用完整路径执行，例如：`/usr/local/Cellar/postgresql@18/18.3/bin/psql`。
