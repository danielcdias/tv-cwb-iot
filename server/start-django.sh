#!/bin/sh
# echo "********** Installing dependencies with pip..."
# pip install -r requirements.txt
echo "********** Waiting database get ready..."
python wait_for_db.py db $MYSQL_USER $MYSQL_PASSWORD $MYSQL_DATABASE 12 5 "SELECT version()"
echo "********** Running Django migrate command..."
python manage.py migrate
echo "********** Running Django collectstatic command..."
python manage.py collectstatic --no-input
# python manage.py collectstatic -link --noinput
chmod 777 /app/static -R
echo "********** Running Django server..."
python manage.py runserver 0.0.0.0:8000
