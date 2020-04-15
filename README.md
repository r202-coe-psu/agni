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
    - [x] display hotspot by date
        - [x] date picker slider -> time slice display
        - [ ] proper implementation
    - [x] performance for faster/smoother points display
        - [x] drawing points in chunk (browser didn't freeze)
        - [ ] FASTER
        - [ ] EVEN FASTERRR
2. data store
    - [ ] write fetcher script
    - [ ] set up influxdb
    - [ ] reshape data to store
    - [ ] make base testing database
3. From weekly meeting
    - [x] check out geopy for geospatial filtering
        - didn't find relevent features though
    - [ ] filter points to contain Thailand and ~10km border around them
        - [x] bounding box filtering
        - [ ] shape filtering
        - [ ] keep points near border (~10km)
            - right now is +- 1 degree in lat/lng from Thailand's bounding box
    - [ ] write acquisitor in agni/acquisitor
        - [x] base functions
        - [ ] standalone executable that can be called from outside
