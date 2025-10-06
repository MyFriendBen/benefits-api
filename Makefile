.PHONY: format
format:
	python -m black . -l 120 --extend-exclude=".*/new_white_label/.*"

COMPOSE_FILE := docker/docker-compose.yml
DOCKER_IMG=benefits-api:benefits-api
DOCKER_NAME=benefits-api
ifeq (, $(shell which docker))
DOCKER_CONTAINER_ID := docker-is-not-installed
else
DOCKER_CONTAINER_ID := $(shell docker ps --filter ancestor=$(DOCKER_IMG) --format "{{.ID}}")
endif

.PHONY: build
build: ## Build Docker image
	docker compose --file $(COMPOSE_FILE) build --force-rm

.PHONY: run
run:  ## Run the app as docker container
	docker compose --file $(COMPOSE_FILE) up

.PHONY: start-db
start-db:  ## Start the local postgresql database
	docker compose --file $(COMPOSE_FILE) up -d pg

.PHONY: console
console:  ## opens a one-off console container
	@docker run -p 8000:8000 -v $(PWD):/code \
   --network policyengine-api_default \
   --rm --name benefits-api-console -it \
   $(DOCKER_IMG) bash
	@docker rm benefits-api-console

CMD := bash
.PHONY: login
login: ## Execute CMD (default: bash shell) in running api container
	docker exec -it $(DOCKER_CONTAINER_ID) $(CMD)

.PHONY: setup-db
setup-db:  ## bootstrap the (local) postgresql database
	psql -U postgres -h localhost -c 'create database benefitsapi'
	psql -U postgres -h localhost -c "create user benefitsapi with login superuser encrypted password 'benefitsapi'"

.PHONY: clean
clean:  ## drop database, clean up files
	psql -U postgres -h localhost -c 'drop database benefitsapi'