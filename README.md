# Brandeis Acoustic Classificaiton & Segmentation tool for CLAMS 

This is a CLAMS app that wraps [Brandeis-ACS](https://pypi.org/project/brandeis-acs/) tool. 

## Installtion 
Clone this repository and install python dependencies listed in [`requirements.txt`](requirements.txt). 
Then run `app.py`. 
You can run it locally (`--once` option), or run it as a web app (without `--once` option).
See `--help` message for more options.

You can also build a docker image with provided [`Dockerfile`](Dockerfile). 
The docker image will run as a web app by default. 