FROM clamsproject/clams-python-ffmpeg-tf2:0.2.2

LABEL maintainer="CLAMS Team <admin@clams.ai>"

RUN mkdir /app
COPY . /app
WORKDIR /app

RUN pip install -r ./requirements.txt

ENTRYPOINT ["python"]
CMD ["app.py"]
