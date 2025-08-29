# Makefile for Creative Automation Pipeline
# Provides common commands for setup and development.

.PHONY: help setup demo clean check-env wait-kafka setup-topics

help:
	@echo "Commands:"
	@echo "  setup          : Install all dependencies for frontend and workers."
	@echo "  check-env      : Check environment configuration and create .env if needed."
	@echo "  run-services   : Start local Kafka via Docker Compose."
	@echo "  wait-kafka     : Wait for Kafka to be ready."
	@echo "  setup-topics   : Create and configure Kafka topics."
	@echo "  stop-services  : Stop local Kafka."
	@echo "  run-dev        : Start all application services in development mode."
	@echo "  demo           : Post a sample brief to the pipeline to trigger a run."
	@echo "  clean          : Remove all generated files and virtual environments."

# =============================================================================
# SETUP & CLEANUP
# =============================================================================

setup:
	@echo "--> Installing frontend dependencies..."
	@cd apps/frontend && pnpm install
	@echo "\n--> Installing Python dependencies for pipeline-worker using UV..."
	@cd apps/pipeline-worker && uv venv && source .venv/bin/activate && uv sync
	@echo "\n--> Installing Python dependencies for agent-worker using UV..."
	@cd apps/agent-worker && uv venv && source .venv/bin/activate && uv sync
	@echo "\n--> Installing realtime-gateway dependencies..."
	@cd apps/realtime-gateway && pnpm install
	@echo "\nSetup complete. Please run 'make check-env' to configure environment."

check-env:
	@echo "--> Checking environment configuration..."
	@if [ ! -f .env ]; then \
		echo "Creating .env file from env.example..."; \
		cp env.example .env; \
		echo "Please review and update .env file with your configuration."; \
	else \
		echo ".env file already exists."; \
	fi
	@echo "--> Environment check complete."

clean:
	@echo "--> Removing Python virtual environments and lock files..."
	@rm -rf apps/pipeline-worker/.venv
	@rm -rf apps/agent-worker/.venv
	@rm -f apps/pipeline-worker/uv.lock
	@rm -f apps/agent-worker/uv.lock
	@echo "--> Removing frontend node_modules..."
	@rm -rf apps/frontend/node_modules
	@rm -rf apps/frontend/.next
	@echo "--> Removing realtime-gateway node_modules..."
	@rm -rf apps/realtime-gateway/node_modules
	@echo "--> Cleaning up Docker containers..."
	@docker compose down -v --remove-orphans
	@echo "\nCleanup complete."

# =============================================================================
# DEVELOPMENT
# =============================================================================

run-services:
	@echo "--> Starting Redpanda (Kafka) and Console via Docker Compose..."
	@docker compose up -d
	@echo "--> Services started. Run 'make wait-kafka' to wait for Kafka to be ready."

wait-kafka:
	@echo "--> Waiting for Kafka to be ready..."
	@echo "--> Checking Kafka health..."
	@until curl -s http://localhost:8080/api/cluster-config > /dev/null 2>&1; do \
		echo "Waiting for Redpanda Console to be ready..."; \
		sleep 5; \
	done
	@echo "--> Redpanda Console is ready at http://localhost:8080"
	@echo "--> Kafka broker should be accessible at localhost:9092"
	@echo "--> You can now run 'make setup-topics' to create required topics"

setup-topics:
	@echo "--> Setting up Kafka topics..."
	@cd apps/pipeline-worker && uv run python ../../scripts/setup-kafka-topics.py
	@echo "--> Topic setup complete. You can now start the application services with 'make run-dev'"

stop-services:
	@echo "--> Stopping Redpanda (Kafka) and Console..."
	@docker compose down

run-dev:
	@echo "--> Starting all services in development mode..."
	@make run-services
	@echo "--> Waiting for Kafka to be ready..."
	@make wait-kafka
	@echo "--> Setting up Kafka topics..."
	@make setup-topics
	@echo "--> Starting application services..."
	@trap 'make stop-services' EXIT; \
	( \
	  (cd apps/frontend && pnpm dev) & \
	  (cd apps/realtime-gateway && pnpm dev) & \
	  (cd apps/pipeline-worker && uv run python main.py) & \
	  (cd apps/agent-worker && uv run python agent_graph.py) & \
	  wait \
	)

demo:
	@echo "--> Submitting sample brief to the pipeline..."
	@curl -X POST -H "Content-Type: application/json" \
	  --data @data/samples/brief_sample.json \
	  http://localhost:3000/api/briefs
	@echo "\n\nCheck the dashboard at http://localhost:3000/dashboard to see the progress."
	@echo "Monitor realtime events at http://localhost:3001/events"

# =============================================================================
# UTILITY COMMANDS
# =============================================================================

logs:
	@echo "--> Showing service logs..."
	@docker compose logs -f

status:
	@echo "--> Checking service status..."
	@docker compose ps
	@echo "\n--> Checking Kafka health..."
	@curl -s http://localhost:3001/health | jq . 2>/dev/null || echo "Realtime gateway not responding"
	@echo "\n--> Checking frontend..."
	@curl -s http://localhost:3000 > /dev/null && echo "Frontend is running" || echo "Frontend not responding"

