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
	- [ ] display plain leaflet map
	- [ ] display hotspot dots
	- [ ] lazy load/draw hotspot marker (with ajax?)
2. data store
	- [ ] write fetcher script
	- [ ] set up influxdb
	- [ ] reshape data to store
