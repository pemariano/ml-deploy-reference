IMAGE_NAME  := mlops-model
LAMBDA_PORT := 9000

.PHONY: help install lint format test build run invoke clean

help:           ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:        ## Install dependencies
	pip install --upgrade pip
	pip install -r requirements.txt

lint:           ## Lint with ruff (check style and static errors)
	ruff check .
	ruff format --check .

format:         ## Auto format code
	ruff format .
	ruff check --fix .

test:           ## Run tests with coverage
	pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=80

build:          ## Build Docker image
	docker build -t $(IMAGE_NAME):latest .

run:            ## Run container locally on port $(LAMBDA_PORT)
	docker run --rm -p $(LAMBDA_PORT):8080 $(IMAGE_NAME):latest

invoke:         ## Invoke the handler locally (requires `make run` in another terminal)
	curl -s -X POST \
		"http://localhost:$(LAMBDA_PORT)/2015-03-31/functions/function/invocations" \
		-H "Content-Type: application/json" \
		-d '{"body": "{\"features\": [1.0, -0.5, 2.3, 0.1]}"}' | python -m json.tool

clean:          ## Remove generated artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	rm -f model.joblib
	docker rmi $(IMAGE_NAME):latest 2>/dev/null || true
