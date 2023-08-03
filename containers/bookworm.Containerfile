FROM docker.io/library/debian:bookworm
RUN apt-get update -y; \
    apt-get install -y \
    python3-django \
    python3-requests \
    python3-django-captcha \
    python3-django-debug-toolbar \
    python3-django-extensions \
    python3-debian \
    python3-debianbts \
    python3-apt \
    python3-gpg \
    python3-yaml \
    python3-bs4 \
    python3-responses \
    python3-pyinotify \
    python3-psycopg2 \
    python3-sphinx \
    python3-sphinx-rtd-theme \
    postgresql \
    python3-selenium \
    chromium-driver \
    wget; \
    wget http://ftp.debian.org/debian/pool/main/p/python-django-jsonfield/python3-django-jsonfield_1.4.0-2_all.deb; \
    apt install ./python3-django-jsonfield_1.4.0-2_all.deb
COPY --chmod=0755 entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
VOLUME /app
CMD ["/app/manage.py", "runserver", "8000"]
