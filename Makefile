.PHONY: format setup

format:
	venv/bin/python -m black .

# Install dev dependencies into venv/ and wire up the pre-commit hook.
setup:
	@test -x venv/bin/pip || { echo "No venv/ found. Create it first: python3.12 -m venv venv"; exit 1; }
	venv/bin/pip install -r requirements-dev.txt
	venv/bin/pre-commit install
