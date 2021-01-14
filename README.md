# NOTE: this is not a definitive README

## Setup

1. At root directory:

    ```sh
    # might have to run twice
    pip install -r requirements.txt
    python setup.py develop
    ```

2. At directory `./agni/web/static`:

    ```sh
    cd agni/web/static
    npm install
    ```

3. Back at root directory again:

    ```sh
    ./scripts/run-web
    ```

4. Web interface accessible at <localhost:8080>

