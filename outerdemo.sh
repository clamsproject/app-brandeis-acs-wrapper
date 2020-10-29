docker run --entrypoint /bin/bash app-audio-segmenter:latest demo.sh
docker cp "$(docker ps -lq)":/segmenter/demo/ ./demo/results/
echo "Done. Check ./demo/results for the results of the demo."
