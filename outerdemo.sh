rm -r ./demo/results-old && mv ./demo/results ./demo/results-old || echo "No old results, continuing"
docker run --entrypoint /bin/bash app-audio-segmenter:latest demo.sh
docker cp "$(docker ps -lq)":/segmenter/demo/ ./demo/results/
docker rm "$(docker ps -lq)"
echo "Done. Check ./demo/results for the results of the demo."
