# Build all container images
build: bullseye bookworm trixie

bullseye:
	podman build -f bullseye.Containerfile . -t distro-tracker:bullseye

bookworm:
	podman build -f bookworm.Containerfile . -t distro-tracker:bookworm

trixie:
	podman build -f trixie.Containerfile . -t distro-tracker:trixie
