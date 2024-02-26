#!make
APP_HOST ?= 0.0.0.0
APP_PORT ?= 8080
EXTERNAL_APP_PORT ?= ${APP_PORT}

run = docker-compose run --rm \
				-p ${EXTERNAL_APP_PORT}:${APP_PORT} \
				-e APP_HOST=${APP_HOST} \
				-e APP_PORT=${APP_PORT} \
				app

.PHONY: image
image:
	docker-compose build

.PHONY: docker-run
docker-run:
	docker-compose up

.PHONY: docker-run-nginx-proxy
docker-run-nginx-proxy:
	docker-compose -f docker-compose.yml -f docker-compose.nginx.yml up

.PHONY: docker-shell
docker-shell:
	$(run) /bin/bash

.PHONY: test
test: run-joplin
	$(run) /bin/bash -c 'export && ./scripts/wait-for-it.sh database:5432 && cd /app/tests/ && pytest -vvv'

.PHONY: run-database
run-database:
	docker-compose run --rm database

.PHONY: run-joplin
run-joplin:
	docker-compose run --rm loadjoplin

.PHONY: install
install:
	pip install -e .[dev,server]

.PHONY: docs-image
docs-image:
	docker-compose -f docker-compose.docs.yml \
		build

.PHONY: docs
docs: docs-image
	docker-compose -f docker-compose.docs.yml \
		run docs

# XLKEY
build:
	docker build --platform linux/amd64 -t xlkeyag/stac-api:latest .

update-prod:
	aws --no-cli-pager ecs describe-task-definition --region ca-central-1 --task-definition xlkey-stac-api-production | \
	jq '.taskDefinition.taskDefinitionArn' | \
	xargs -I {} aws --no-cli-pager ecs update-service --region ca-central-1 --cluster XLKEY_PRODUCTION_EKS_CLUSTER --service xlkey-stac-api-production --force-new-deployment --task-definition {}

task-prod:
	aws ecs register-task-definition --region ca-central-1 --cli-input-json file://task-definition.json