LATEST_RELEASE := $(shell gh release list -L 1 | awk '{print $$1}' | sed 's/v//')
NEXT_RELEASE_VERSION := $(shell echo $(LATEST_RELEASE) | awk -F. '{$$NF = $$NF + 1;} 1' | sed 's/ /./g')

.PHONY: bump
bump:
	@if [ "$(shell awk -F'"' '/^version = / {print $$2}' pyproject.toml)" = "$(LATEST_RELEASE)" ]; then \
		echo "Version out of sync. Expected $(NEXT_RELEASE_VERSION), found $(shell awk -F'"' '/^version = / {print $$2}' pyproject.toml)"; \
		echo "Syncing version to $(NEXT_RELEASE_VERSION)"; \
		sed -i '' "s/version = \".*\"/version = \"$(NEXT_RELEASE_VERSION)\"/" pyproject.toml; \
		exit 1; \
	fi
	@echo "Update version to $(NEXT_RELEASE_VERSION)"
	@sed -i '' "s/version = \".*\"/version = \"$(NEXT_RELEASE_VERSION)\"/" pyproject.toml

.PHONY: release
release:
	@git commit -m "Update version to $(NEXT_RELEASE_VERSION)"
	@git push
	@gh release create v$(NEXT_RELEASE_VERSION) --generate-notes

.PHONY: re-release
re-release:
	@gh release delete v$(LATEST_RELEASE) --yes
	@git push origin :refs/tags/v$(LATEST_RELEASE)
	@gh release create v$(LATEST_RELEASE) --generate-notes
