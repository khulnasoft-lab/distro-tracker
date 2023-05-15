FROM debian:stable

EXPOSE 8000

WORKDIR /distro-tracker

ARG NON_INTERACTIVE="1"
ARG DOCKER_ENVIRONMENT="1"
ARG DEBIAN_FRONTEND=noninteractive
ARG DEBCONF_NOWARNINGS="yes"

COPY bin/quick-setup.sh /distro-tracker/bin/quick-setup.sh
COPY distro_tracker/project/settings/local.py.sample-debian-dev distro_tracker/project/settings/local.py.sample-debian-dev

RUN apt-get update && apt-get upgrade -y && \
    ./bin/quick-setup.sh install_packages && \
    apt-get -q -y clean && \
    rm -rf /var/lib/apt/lists/*

COPY . /distro-tracker

ENTRYPOINT ["./bin/docker-entrypoint.sh"]
