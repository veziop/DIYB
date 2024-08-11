FROM alpine:latest

RUN apk add --no-cache sqlite

WORKDIR /data

RUN if [ ! -f /data/database.db ]; then \
        sqlite3 /data/database.db "VACUUM;"; \
    fi

VOLUME /data

CMD ["tail", "-f", "/dev/null"]
