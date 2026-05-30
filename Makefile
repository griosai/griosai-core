.PHONY: validate test compile schema-smoke doctor-smoke lineage-smoke kustomize

PYTHON ?= python3

validate:
	./scripts/validate.sh

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests

compile:
	PYTHONPATH=src $(PYTHON) -m compileall src/griosai

schema-smoke:
	PYTHONPATH=src $(PYTHON) -m griosai.cli analysis-schema >/dev/null
	PYTHONPATH=src $(PYTHON) -m griosai.cli validate-analysis --json-file examples/sample-analysis.json --json

doctor-smoke:
	TMPDIR="$$(mktemp -d)"; \
	PYTHONPATH=src $(PYTHON) -m griosai.cli init --vault "$$TMPDIR/vault" >/dev/null; \
	PYTHONPATH=src $(PYTHON) -m griosai.cli doctor --vault "$$TMPDIR/vault" --repo . --json; \
	rm -rf "$$TMPDIR"

lineage-smoke:
	TMPDIR="$$(mktemp -d)"; \
	PYTHONPATH=src $(PYTHON) -m griosai.cli sample --vault "$$TMPDIR/vault" >/dev/null; \
	PYTHONPATH=src $(PYTHON) -m griosai.cli lineage-verify --vault "$$TMPDIR/vault" --json; \
	rm -rf "$$TMPDIR"

kustomize:
	kubectl kustomize deploy/kubernetes/base >/dev/null
	kubectl kustomize deploy/kubernetes/mlflow >/dev/null
