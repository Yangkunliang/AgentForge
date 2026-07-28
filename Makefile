# AgentForge 本地开发便捷脚本
#
# 最常见用法:
#   make dev      一键拉起 基础设施 + 迁移 + 后端(后台) + 前端(前台)
#   make stop     停止后端与容器
#
# 各子命令:
#   make infra      启动 Docker 基础设施 (Postgres/RabbitMQ/Redis)
#   make migrate    执行数据库迁移 (alembic upgrade head)
#   make api        前台启动 FastAPI (热重载, 端口 8000)
#   make web        前台启动前端 Vite dev server (端口 3000)
#   make dev-bg     仅后端: 基础设施 + 迁移 + API(后台)
#   make down       停止并移除容器 (保留数据卷)
#   make ps         查看容器状态
#   make logs       跟踪基础设施日志
#   make health     探测后端健康端点
#   make revision m="说明"   生成 autogenerate 迁移

.ONESHELL:
.PHONY: infra migrate api web dev dev-bg down stop ps logs health revision

VENV ?= .venv
AK := PYTHONPATH=src $(VENV)/bin/alembic -c migrations/alembic.ini
COMPOSE := docker compose
API_PID := /tmp/agentforge-api.pid
API_LOG := /tmp/agentforge-api.log

infra:
	$(COMPOSE) up -d

migrate:
	$(AK) upgrade head

api:
	PYTHONPATH=src $(VENV)/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload --log-level info

web:
	cd web && npm run dev

# 等待 Postgres 健康
define wait_pg
	@for i in $$(seq 1 30); do \
	  docker exec agentforge-postgres-1 pg_isready -U agent -d agentforge >/dev/null 2>&1 && break; \
	  sleep 2; \
	  done
endef

dev-bg: infra
	$(call wait_pg)
	$(AK) upgrade head
	PYTHONPATH=src $(VENV)/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --log-level info > $(API_LOG) 2>&1 &
	echo $$! > $(API_PID)
	@echo "API 已在后台启动 (pid $$(cat $(API_PID))), 日志: $(API_LOG)"
	@echo "健康检查: make health"

dev: dev-bg
	@echo "前端启动中... (Ctrl+C 退出时会一并停止后端)"
	trap 'kill $$(cat $(API_PID)) 2>/dev/null; rm -f $(API_PID); echo; echo "已停止后端"' EXIT INT TERM
	cd web && npm run dev

stop:
	@if [ -f $(API_PID) ]; then kill $$(cat $(API_PID)) 2>/dev/null && echo "已停止后端"; rm -f $(API_PID); fi

down: stop
	$(COMPOSE) down

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

health:
	@curl -s http://127.0.0.1:8000/api/v1/health || echo "后端未响应"

revision:
	$(AK) revision --autogenerate -m "$(m)"
