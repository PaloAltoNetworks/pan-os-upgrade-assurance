lint:
	flake8 panos_upgrade_assurance

security:
	bandit -c pyproject.toml -r .

format_check:
	black --diff --check panos_upgrade_assurance

format:
	black panos_upgrade_assurance

documentation:
	pydoc-markdown