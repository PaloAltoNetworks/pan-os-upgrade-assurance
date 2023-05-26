lint:
	flake8 --config .flake8 panos_upgrade_assurance

security:
	bandit -c pyproject.toml -r .

format:
	black -v --diff --check panos_upgrade_assurance

documentation:
	pydoc-markdown