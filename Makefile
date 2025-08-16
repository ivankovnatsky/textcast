.PHONY: dev
dev:
	nix develop --extra-experimental-features flakes --extra-experimental-features nix-command

.PHONY: bump
bump:
	$(eval LATEST_RELEASE := $(shell gh release list -L 1 | awk '{print $$1}' | sed 's/v//'))
	$(eval NEXT_RELEASE_VERSION := $(shell echo $(LATEST_RELEASE) | awk -F. '{$$NF = $$NF + 1;} 1' | sed 's/ /./g'))
	@echo "Updating version to $(NEXT_RELEASE_VERSION)"
	@sed 's/version = ".*"/version = "$(NEXT_RELEASE_VERSION)"/' pyproject.toml > pyproject.toml.tmp
	@mv pyproject.toml.tmp pyproject.toml

.PHONY: release
release:
	$(eval LATEST_RELEASE := $(shell gh release list -L 1 | awk '{print $$1}' | sed 's/v//'))
	$(eval NEXT_RELEASE_VERSION := $(shell echo $(LATEST_RELEASE) | awk -F. '{$$NF = $$NF + 1;} 1' | sed 's/ /./g'))
	@git add .
	@git commit -m "Update version to $(NEXT_RELEASE_VERSION)"
	@git push
	@gh release create v$(NEXT_RELEASE_VERSION) --generate-notes

.PHONY: re-release
re-release:
	$(eval LATEST_RELEASE := $(shell gh release list -L 1 | awk '{print $$1}' | sed 's/v//'))
	$(eval NEXT_RELEASE_VERSION := $(shell echo $(LATEST_RELEASE) | awk -F. '{$$NF = $$NF + 1;} 1' | sed 's/ /./g'))
	@gh release delete v$(NEXT_RELEASE_VERSION) --cleanup-tag || true
	@git push
	@gh release create v$(NEXT_RELEASE_VERSION) --generate-notes

.PHONY: cast
cast:
	@python -m textcast \
		--directory /Volumes/Storage/Data/Textcast/Audio \
		--file-url-list /Volumes/Storage/Data/Textcast/Texts/Texts.txt \
		--condense \
		--condense-ratio 0.5 \
		--yes \
		--abs-url "$$ABS_URL" \
		--abs-pod-lib-id "db54da2c-dc16-4fdb-8dd4-5375ae98f738" \
		--abs-pod-folder-id "c9d67ffa-8e94-41f6-b22d-3924cf9ff511"

.PHONY: watch-cast
watch-cast:
	while true; do \
		watchman-make \
			--root /Volumes/Storage/Data/Textcast/Texts \
			--pattern "Texts.txt" \
			--make "cd $(shell pwd) && nix develop --command make" \
			--target cast; \
		echo "watchman-make exited, restarting..."; \
		sleep 1; \
	done
