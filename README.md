# app-audio-segmenter v0.3.0

To run the demo on the provided mp3 file, first build the Docker image, then run the outer demo script:

```
$ docker build -t app-audio-segmenter:latest -t app-audio-segmenter:0.3.0 .
$ chmod +x outerdemo.sh
$ ./outerdemo.sh
```

Open the newly created `demo/results` to see the generated tsv file (for comparison) and MMIF files.

To run the app as a Flask app, build the image and run the container in the usual CLAMS-y way.

Command line API for `app.py`:

```
usage: app.py [-h] [--once PATH] [--pretty] [--save-tsv]

optional arguments:
  -h, --help   show this help message and exit
  --once PATH  Use this flag if you want to run the segmenter on a path you
               specify, instead of running the Flask app.
  --pretty     Use this flag to return "pretty" (indented) MMIF data.
  --save-tsv   Use this flag to preserve the intermediary TSV file generated
               by the segmenter.
```
