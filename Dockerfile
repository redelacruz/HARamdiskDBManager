FROM python:slim

RUN apt-get update && \
      apt-get -y install sudo

RUN passwd_hash=$(openssl rand -base64 32)
RUN useradd -m -p "$passwd_hash" docker
RUN usermod -aG sudo docker
RUN echo '%docker ALL=(ALL) NOPASSWD: /bin/chown' >> /etc/sudoers

WORKDIR /app/

COPY ./healthcheck.sh /app/
COPY ./db_copy.py /app/
COPY ./requirements.txt /app/

RUN chown -R docker:docker /app/
RUN chmod +x /app/healthcheck.sh

USER docker

RUN pip install -r requirements.txt
ENV PYTHONUNBUFFERED=1
ENV DB_FILENAME="home-assistant_v2.db"
ENV RAMDISK_PATH="/mount/"
ENV STORAGE_PATH="/storage/"
ENV PATH="$PATH:/app"

HEALTHCHECK --start-period=60s --interval=60s --timeout=10s --retries=3 CMD ["healthcheck.sh"]

CMD ["python", "-u", "db_copy.py"]