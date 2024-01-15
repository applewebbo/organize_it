.PHONY: server

local:
	python manage.py runserver --settings=core.settings.development

requirements:
	pip install --upgrade pip pip-tools
	pip-compile --resolver=backtracking --strip-extras
	pip install -r requirements-dev.txt -r requirements.txt

checkmigrations:
	python manage.py makemigrations --check --no-input --dry-run

watch:
	npm run dev

test:
	pytest --cov-report html:htmlcov --cov-report term:skip-covered

mptest:
	pytest -m "not mapbox" --cov-report html:htmlcov --cov-report term:skip-covered
