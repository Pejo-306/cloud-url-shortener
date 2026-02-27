# Port configuration (override via: make up REDIS_PORT=7000)
REDIS_PORT				?= 6379
REDISINSIGHT_PORT		?= 5540
APPCONFIG_AGENT_PORT	?= 2772
LOCALSTACK_EDGE_PORT	?= 4566
LOCALSTACK_AUX_PORT		?= 4571

COMPOSE_ENV = REDIS_PORT=$(REDIS_PORT) \
			  REDISINSIGHT_PORT=$(REDISINSIGHT_PORT) \
			  APPCONFIG_AGENT_PORT=$(APPCONFIG_AGENT_PORT) \
			  LOCALSTACK_EDGE_PORT=$(LOCALSTACK_EDGE_PORT) \
			  LOCALSTACK_AUX_PORT=$(LOCALSTACK_AUX_PORT)

.PHONY: up down destroy restart help

help:
	@echo "Local Docker Compose stack management"
	@echo ""
	@echo "\033[1mTargets:\033[0m"
	@echo "  make up                                  - Create and start the stack (detached)"
	@echo "  make down                                - Stop and remove the stack"
	@echo "  make destroy                             - Stop and remove volumes & images (\033[1mWARNING\033[0m: you will lose all data)"
	@echo "  make restart                             - Restart the stack"
	@echo "  make help                                - Show this message"
	@echo ""
	@echo "\033[1mConfigurable ports:\033[0m (override via: make up REDIS_PORT=7000)"
	@echo "  REDIS_PORT                               - Redis database"
	@echo "  REDISINSIGHT_PORT                        - Redis Insight web UI"
	@echo "  APPCONFIG_AGENT_PORT                     - AWS AppConfig Agent"
	@echo "  LOCALSTACK_EDGE_PORT                     - LocalStack main edge / AWS API"
	@echo "  LOCALSTACK_AUX_PORT                      - LocalStack auxiliary gateway"
	@echo ""
	@echo "Example: make up REDIS_PORT=7000"

up:
	$(COMPOSE_ENV) docker compose up -d

down:
	$(COMPOSE_ENV) docker compose down

destroy:
	$(COMPOSE_ENV) docker compose down -v --rmi all

restart: down up
