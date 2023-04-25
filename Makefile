PATH:=bin/:${PATH}
.PHONY: update-deps init update clean test build push

API_IMAGE = lsstsqre/squash-api

help:
	@echo "Available commands:"
	@echo "  update-deps update dependencies"
	@echo "  init    install develop version"
	@echo "  update  update dependencies and install develop version"
	@echo "  clean			remove temp files"
	@echo "  test			run tests and generate test coverage"
	@echo "  build          build squash-api docker image"
	@echo "  push           push docker images to docker hub"


update-deps:
	pip install --upgrade pip-tools pip setuptools
	pip-compile --upgrade --build-isolation --generate-hashes --output-file requirements/main.txt requirements/main.in
	pip-compile --upgrade --build-isolation --generate-hashes --output-file requirements/dev.txt requirements/dev.in
	pip-sync requirements/main.txt requirements/dev.txt

init:
	pip install --editable .
	pip install --upgrade -r requirements/main.txt -r requirements/dev.txt
	rm -rf .tox
	pip install --upgrade tox
	pre-commit install

update: update-deps init

clean:
	find ./ -type f -name '*.pyc' -exec rm -f {} \;
	rm -rf .coverage*
	rm -rf .cache
	rm -rf .tox
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	rm -rf dist
	rm -rf build

test:
	flake8 app tests
	coverage run --source=app test.py

build: check-tag
	docker build -t $(API_IMAGE):${TAG} .

push: check-tag
	docker push $(API_IMAGE):${TAG}

check-tag:
	@if test -z ${TAG}; then echo "Error: TAG is undefined."; exit 1; fi
