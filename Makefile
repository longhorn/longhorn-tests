MACHINE := longhorn

.PHONY: validate ci

buildx-machine:
	@docker buildx create --name=$(MACHINE) 2>/dev/null || true

validate:
	docker buildx build --target validate -f Dockerfile .

ci:
	docker buildx build --target ci-artifacts --output type=local,dest=. -f Dockerfile .

.DEFAULT_GOAL := ci
