build:
	docker build \
	-t distro-tracker .

quick-setup:
	docker run -it --rm \
		--entrypoint="" \
		-v $(PWD):/distro-tracker \
		distro-tracker \
		./bin/quick-setup.sh

run:
	docker run -it \
		-v $(PWD):/distro-tracker \
		-p 8000:8000 \
		distro-tracker

test:
	docker run -it \
		--entrypoint="tox" \
		-v $(PWD):/distro-tracker \
		-p 8000:8000 \
		distro-tracker

shell:
	docker run -it --rm \
		--entrypoint="" \
		-v $(PWD):/distro-tracker \
		distro-tracker \
		bash
