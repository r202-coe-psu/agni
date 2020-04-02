*NOTE: this is not a definitive README, merely a reminder for self.*

# Setup

At root directory:

```sh
python setup.py develop
```

at `agni/web/static`:

```sh
cd agni/web/static
npm install
```

back at root directory again:

```sh
./scripts/run-web
```

# Known Tasks

1. web app
    - [x] get brython to run
    - [x] display plain leaflet map
    - [x] display hotspot dots
    - [x] lazy load/draw hotspot marker (with ajax?)
        - [ ] proper endpoints for ajax data retrieval
        - still load all data at once. let's see how well this holds up
    - [ ] display hotspot by date
    - [ ] date picker slider -> time slice display
2. data store
    - [ ] write fetcher script
    - [ ] set up influxdb
    - [ ] reshape data to store
    - [ ] make base testing database
3. From weekly meeting
    - [ ] check out geopy for geospatial filtering
    - [ ] filter points to contain Thailand and ~10km border around them
    - [ ] write acquisitor in agni/acquisitor
