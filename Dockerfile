FROM clamsproject/clams-python-ffmpeg:0.2.1

LABEL maintainer="CLAMS Team <admin@clams.ai>"

RUN apt-get update && apt-get install -y libsndfile1

RUN mkdir /segmenter
COPY . /segmenter
WORKDIR /segmenter

RUN mkdir ./data

RUN git clone --depth 1 --branch v1.1 https://github.com/brandeis-llc/acoustic-classification-segmentation.git

RUN pip install -r ./acoustic-classification-segmentation/requirements.txt
RUN pip install -r ./requirements.txt

ENTRYPOINT ["python"]
CMD ["app.py"]
