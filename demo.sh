#!/bin/bash
find demo/ -type f ! -name '*.mp3' -delete
clams source audio:/segmenter/demo/cpb-aacip-259-dj58gh9t.h264.mp4.mp3 > demo/dj58gh9t.json
python app.py --once demo/dj58gh9t.json --pretty --save-tsv
mv mmif_out.json demo/
mv segmented.tsv demo/
rm demo/cpb-aacip-259-dj58gh9t.h264.mp4.mp3
