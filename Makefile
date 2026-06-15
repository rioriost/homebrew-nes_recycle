SHELL := /bin/sh

REPO_ROOT := $(CURDIR)
UV ?= uv
DIST_DIR := $(REPO_ROOT)/dist
FORMULA_DIR := $(REPO_ROOT)/Formula
FORMULA_FILE := $(FORMULA_DIR)/nes_recycle.rb
EXTENSION_DIR := $(REPO_ROOT)/extension
EXTENSION_VERSION := $(shell python3 -c 'import json; print(json.load(open("$(EXTENSION_DIR)/manifest.json"))["version"])' 2>/dev/null)
EXTENSION_ZIP := $(DIST_DIR)/nes_recycle_extension-$(EXTENSION_VERSION).zip
SAFARI_APP_NAME ?= nes_recycle
SAFARI_BUNDLE_IDENTIFIER ?= st.rio.nesrecycle

.PHONY: release-artifacts sync build formula extension-icons extension-validate extension-package safari-project

release-artifacts: sync build formula

sync:
	$(UV) sync --extra test --group dev

build:
	rm -rf "$(DIST_DIR)"
	$(UV) build

formula:
	mkdir -p "$(FORMULA_DIR)"
	genformula \
		--source-subdir . \
		--pyproject "$(REPO_ROOT)/pyproject.toml" \
		--output "$(FORMULA_FILE)"

extension-icons:
	python3 "$(EXTENSION_DIR)/tools/generate_icons.py"

extension-validate: extension-icons
	python3 -m json.tool "$(EXTENSION_DIR)/manifest.json" >/dev/null
	@if command -v node >/dev/null 2>&1; then \
		for file in "$(EXTENSION_DIR)"/*.js; do node --check "$$file"; done; \
	else \
		echo "node not found; skipped JavaScript syntax checks"; \
	fi

extension-package: extension-validate
	mkdir -p "$(DIST_DIR)"
	rm -f "$(EXTENSION_ZIP)"
	cd "$(EXTENSION_DIR)" && zip -qr "$(EXTENSION_ZIP)" . \
		-x "*.DS_Store" \
		-x "__MACOSX/*" \
		-x "README.md" \
		-x "tools/*"
	@unzip -p "$(EXTENSION_ZIP)" manifest.json | python3 -m json.tool >/dev/null
	@echo "$(EXTENSION_ZIP)"

safari-project: extension-validate
	mkdir -p "$(REPO_ROOT)/build/safari"
	xcrun safari-web-extension-converter "$(EXTENSION_DIR)" \
		--project-location "$(REPO_ROOT)/build/safari" \
		--app-name "$(SAFARI_APP_NAME)" \
		--bundle-identifier "$(SAFARI_BUNDLE_IDENTIFIER)" \
		--macos-only \
		--copy-resources \
		--no-open \
		--no-prompt \
		--force
