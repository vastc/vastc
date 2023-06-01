## Configuration

Copy listener.ini.example to listener.ini and chnage to the required values.

## Docker

### Building and Running the Docker Image

`docker build -t vastc-pipeline .` 
`docker run --rm -p 8104:8104 -v $(pwd)/listener.ini:/app/listener.ini vastc-pipeline`
