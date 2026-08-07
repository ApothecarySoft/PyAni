#!/bin/sh

DB_DIR=~/Documents/pyani/cache
DB_FILENAME=db.lbdb
DB_PATH="$DB_DIR"/"$DB_FILENAME"

chmod -R 777 "$DB_DIR"

if [ ! -f "$DB_PATH" ]; then
  echo "$DB_PATH does not exist. Try running Anilist Toolkit to create the database" >&2
  exit 1
fi

echo "http://localhost:8000"

docker run --rm -p 8000:8000 \
  -v "$DB_DIR":/database \
  -e LBUG_FILE=$DB_FILENAME \
  -e MODE=READ_ONLY \
  ghcr.io/ladybugdb/explorer:latest \
  > /dev/null
