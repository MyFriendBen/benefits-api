.PHONY: format setup

format:
	python -m black . -l 120

# Install dev dependencies into venv/ and wire up the pre-commit hook.
setup:
	venv/bin/pip install -r requirements-dev.txt
	venv/bin/pre-commit install
