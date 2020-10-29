# app-audio-segmenter

To run the demo on the provided mp3 file, first build the Docker image, then run the outer demo script:

```
$ docker build -t app-audio-segmenter:latest -t app-audio-segmenter:0.1.0 .
$ chmod +x outerdemo.sh
$ ./outerdemo.sh
```

Open the newly created `demo/results` to see the generated tsv file (for comparison) and MMIF files.

To run the app as a Flask app, build the image and run the container in the usual CLAMS-y way.
