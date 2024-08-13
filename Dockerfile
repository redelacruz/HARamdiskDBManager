FROM python:slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
      apt-get -y install sudo

RUN useradd -m docker && echo "docker:docker" | chpasswd && adduser docker sudo

WORKDIR /app/

ENV DB_FILENAME="home-assistant_v2.db"
ENV RAMDISK_PATH="/mount/"
ENV STORAGE_PATH="/storage/"
ENV PATH="$PATH:/app"

COPY ./docker-entrypoint.sh /app/
COPY ./healthcheck.sh /app/
COPY ./db_copy.py /app/
COPY ./requirements.txt /app/

RUN pip install -r requirements.txt

RUN chown -R docker:docker /app/
RUN chmod +x /app/docker-entrypoint.sh
RUN chmod +x /app/healthcheck.sh

USER docker

HEALTHCHECK --start-period=60s --interval=60s --timeout=10s --retries=3 CMD ["healthcheck.sh"]

ENTRYPOINT ["docker-entrypoint.sh"]