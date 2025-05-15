.phony: lint
lint:
	flake8 panos_upgrade_assurance tests

.phony: security
security:
	bandit -c pyproject.toml -r panos_upgrade_assurance tests

.phony: format_check
format_check:
	black --diff --check panos_upgrade_assurance tests

.phony: format
format:
	black panos_upgrade_assurance tests

.phony: test_coverage
test_coverage:
	pytest --cov panos_upgrade_assurance --cov-report=term-missing --cov-report=xml:coverage.xml

.phony: documentation
documentation:
	pydoc-markdown

.phony: check_line_length
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

.phony: all
all: lint format security test_coverage

.phony: sca
sca: format lint security
