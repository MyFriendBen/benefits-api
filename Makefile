setup:
	pip install -r requirements.txt
	venv/bin/pre-commit install

format:
	python -m black . -l 120 --extend-exclude=".*/new_white_label/.*"
