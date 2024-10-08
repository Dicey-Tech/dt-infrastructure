help: ## display this help message
	@echo "Please use \`make <target>' where <target> is one of"
	@grep '^[a-zA-Z]' $(MAKEFILE_LIST) | sort | awk -F ':.*?## ' 'NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

EDUCATE = educate_infrastructure/applications/educate
NETWORKING = educate_infrastructure/infra/network
DATABASES = educate_infrastructure/databases

dev.setup:
	pip install -r requirements.txt
	pre-commit install

up:
	docker-compose up -d 

build:
	docker-compose build

stop:
	docker-compose stop

pull:
	docker pull pulumi/pulumi-python 
	docker-compose build

preview.databases:
	pulumi preview -C $(DATABASES)

preview.educate:
	pulumi preview -C $(EDUCATE)

preview.networking:
	pulumi preview -C $(NETWORKING)
	#docker run --rm -ti -v ~/.pulumi:/root/.pulumi -v $(pwd):/pulumi/projects diceytech/pulumi cd networking && pulumi preview --stack prod -C educate_infrastructure/applications/educate

up.databases:
	pulumi up -C $(DATABASES) -y

up.educate:
	pulumi up -C $(EDUCATE) -y

up.networking:
	pulumi up -C $(NETWORKING) -y

destroy.all: #TODO control how/who can use it
	make destroy.educate destroy.databases destroy.networking

destroy.databases:
	pulumi destroy -C $(DATABASES) -y

destroy.educate:
	pulumi destroy -C $(EDUCATE) -y

destroy.networking:
	pulumi destroy -C $(NETWORKING) -y

connect.educate: #TODO Fix command
	aws ssm start-session --target $(pulumi -C src/educate_infrastructure/applications/educate stack output instanceId)

test: # TODO change it to run in the container
	python -m pytest --disable-pytest-warnings

clean: ## remove generated byte code and build artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {}

requirements:
	pip install -r requirements.txt

isort:
	isort .