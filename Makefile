.PHONY: server

local:
	python manage.py runserver --settings=core.settings.development

requirements:
	uv sync

migrate:
	python manage.py migrate --settings=core.settings.development

watch:
	npm run dev

build:
	npm run build

test:
	pytest

ftest:
	pytest -n 8 --reuse-db

mptest:
	pytest -m "not mapbox" --cov-report html:htmlcov --cov-report term:skip-covered --cov-fail-under 100

dockerdb:
	docker compose exec web python manage.py flush --no-input --settings=core.settings.production
	docker compose exec web python manage.py migrate --settings=core.settings.production
	docker compose exec web python manage.py populate_trips --settings=core.settings.production

cluster:
	python manage.py qcluster --settings=core.settings.development
