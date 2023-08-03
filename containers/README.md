The various containers that can be created with "make" can be used to run
tests for various targets:

- bullseye is Debian 11 with Django 3.2 from bullseye-backports
- bookworm is Debian 12 with Django 3.2
- trixie is expected to be Debian 13 with Django 4.2, but is currently
  Debian unstable with Django 4.2 from experimental

From the top-level distro-tracker source directory, you can run a test
container with a command like this one:

$ podman run --rm -v .:/app -ti distro-tracker:bookworm /bin/bash
