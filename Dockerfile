FROM clamsproject/clams-python-ffmpeg-tf2:0.4.3

LABEL maintainer="CLAMS Team <admin@clams.ai>"

RUN mkdir /app
COPY . /app
WORKDIR /app

RUN pip install -r ./requirements.txt

CMD ["python", "app.py"]
