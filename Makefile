LATEST_RELEASE := $(shell gh release list -L 1 | awk '{print $$1}' | sed 's/v//')
NEXT_RELEASE_VERSION := $(shell echo $(LATEST_RELEASE) | awk -F. '{$$NF = $$NF + 1;} 1' | sed 's/ /./g')

.PHONY: bump
bump:
	@echo "Updating version to $(NEXT_RELEASE_VERSION)"
	@sed 's/version = ".*"/version = "$(NEXT_RELEASE_VERSION)"/' pyproject.toml > pyproject.toml.tmp
	@mv pyproject.toml.tmp pyproject.toml

.PHONY: release
release:
	@git add .
	@git commit -m "Update version to $(NEXT_RELEASE_VERSION)"
	@git push
	@gh release create v$(NEXT_RELEASE_VERSION) --generate-notes

.PHONY: re-release
re-release:
	@gh release delete v$(NEXT_RELEASE_VERSION) --cleanup-tag || true
	@git push
	@gh release create v$(NEXT_RELEASE_VERSION) --generate-notes

.PHONY: cast
cast:
	@python -m articast \
		--directory ~/Library/Mobile\ Documents/com~apple~CloudDocs/Podcasts/Audio \
		--file-url-list ~/Library/Mobile\ Documents/com~apple~CloudDocs/Podcasts/Articles/Articles.txt \
		--condense \
		--condense-ratio 0.4 \
		--yes
