
## Configuration

Copy listener.ini.example to listener.ini and chnage to the required values.
If filtering of recieved series based on series descriptions is required create the series-descriptions.txt file with one accepted series description per line.

## Docker

### Building and Running the Docker Image

`docker build -t vastc-anon-listener .`
`docker run --rm -p 8104:8104 -v $(pwd)/series-descriptions.txt:/app/series-descriptions.txt -v $(pwd)/listener.ini:/app/listener.ini vastc-anon-listener`
