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

check_line_length:
	@for FILE in $$(ls panos_upgrade_assurance/[a-z]*.py); do \
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

all: lint format security documentation
