FROM factrc/python2:v1
WORKDIR /app
COPY ./app/app.py app.py
COPY ./app/config.json config.json
CMD [ "python2", "app.py" ]
