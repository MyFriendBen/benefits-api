format:
	python -m black . -l 120 --extend-exclude=".*/new_white_label/.*"

# dbt commands
.PHONY: dbt-version dbt-debug dbt-build dbt-test dbt-docs dbt-docs-serve dbt-clean

dbt-version:
	cd dbt && dbt --version

dbt-debug:
	cd dbt && dbt debug

dbt-build:
	cd dbt && dbt build

dbt-test:
	cd dbt && dbt test

dbt-docs:
	cd dbt && dbt docs generate

dbt-docs-serve:
	cd dbt && dbt docs serve

dbt-clean:
	cd dbt && dbt clean

dbt-run:
	cd dbt && dbt run
