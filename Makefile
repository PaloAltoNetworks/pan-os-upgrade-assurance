lint:
	flake8 panos_upgrade_assurance tests

security:
	bandit -c pyproject.toml -r .

format_check:
	black --diff --check panos_upgrade_assurance tests

format:
	black panos_upgrade_assurance tests

test_coverage:
	pytest --cov panos_upgrade_assurance --cov-report=term-missing --cov-report=xml:coverage.xml

documentation:
	pydoc-markdown

check_line_length:
	@for FILE in $$(find . -type f -name '*.py'); do \
		echo $$FILE; \
		LN=0; \
		while read -r line; do \
			LN=$$(($$LN + 1)); \
			LL=$$(awk '{print length}' <<< "$$line"); \
			if [ $$LL -gt 130 ]; then \
				echo "  line: $$LN, length: $$LL"; \
			fi; \
		done < "$$FILE"; \
	done

all: format lint security test_coverage documentation
