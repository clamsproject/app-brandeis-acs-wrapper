FROM clamsproject/clams-python-ffmpeg:0.2.1

LABEL maintainer="CLAMS Team <admin@clams.ai>"

RUN mkdir /app
COPY . /app
WORKDIR /app

RUN pip install -r ./requirements.txt

ENTRYPOINT ["python"]
CMD ["app.py"]
