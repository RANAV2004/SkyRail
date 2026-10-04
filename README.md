# RailSky

Train search and route planning for Indian Railways, with a delay model trained on real
running data and the weather along the way.

This started as two separate projects of mine. One was my college minor project, a train
ticket scheduler that finds the shortest route with Dijkstra on 17 made-up stations. The
other was [CLOUDY](https://github.com/RANAV2004/CLOUDY), a React weather app. I merged
them, then swapped the toy network for the real one: 4,735 stations, 9,331 track links and
3,786 trains, plus a LightGBM model trained on 1.17 million real arrival records from
September 2024.

## What it does

**Passengers** search From, To and a date ("Hyderabad" covers Secunderabad, Hyderabad
Deccan, Kacheguda and Lingampalli). They get every train that runs between them that day,
sorted by timetable time plus the delay the model expects, so a train that's quicker on
paper but usually runs 2 hours late drops down the list. Each train shows its number, an
expected delay with an "up to" figure, and the forecast at its main stops for the time the
train gets there. "Book on IRCTC" opens irctc.co.in with the station codes and train number
shown, because I didn't want to fake a booking system. Trips can be saved to keep checking
the forecast before travelling.

**The admin** gets the route planner, weather for any station (this page is basically
CLOUDY), a report on how the delay model did, and a user list where they can reset
passwords. There's one admin account, made on startup; sign-up only creates passengers.
The admin can't see passwords since only bcrypt hashes are stored.

## The route planner, and why Yen's algorithm didn't work

The first version used Yen's K-shortest paths to get 4 alternatives. On the 17-city network
that was fine. On the real one, Secunderabad to Howrah gave me 4 "different" routes that
shared 97 to 99% of their track. Yen's finds the next shortest path, and on a real network
that's the same line with a 2 km detour through a different junction.

So `alternative_routes()` in `backend/route_planner.py` uses the penalty method instead:

1. Find the shortest path with Dijkstra.
2. Make every track within 25 km of that path 3 times as expensive and search again. This
   pushes the next search onto a different corridor rather than a side loop.
3. Keep the new path only if under 60% of its stations are within 30 km of an earlier
   route, and it's no more than 1.5 times the shortest distance.

For Secunderabad to Howrah this gives the coast line via Vijayawada and Visakhapatnam, an
inland line via Kazipet, Balharshah, Gondia and Raipur, one through Jabalpur and one via
Nagpur. The test `test_yen_gives_near_duplicates_on_the_real_network` keeps the Yen's
result around as proof of the problem.

For each route the planner works out the ETA at about 10 key stops (the busiest station in
each stretch of the line), looks up the forecast at that time, turns it into delay minutes
with simple rules (thunderstorm 90 min, heavy rain 55, fog under 200 m 90, and so on) and
recommends whichever arrives first. The API also returns the reasoning in plain English
(`reasons` in the `/admin/weather-route` response), for example:

> Going through Kazipet, Balharshah, Gondia and Raipur adds 96 km over the shortest route,
> but it should arrive about 1h 16m sooner. Route A loses 3h 40m to weather. The worst of
> it is thunderstorm near Vizianagram around Fri 15:06.

That was one run on demo weather. With a real API key the answer changes with the
forecast.

## The delay model

`scripts/train_delay_model.py` trains two LightGBM quantile models on the RSTGCN delay
records: one for the median delay and one for the 90th percentile (the "up to" number).
I split by time, training on 1 to 23 September and testing on 24 to 30 September, so the
model is always predicting a week it hasn't seen.

| Approach | Average error on the test week |
|---|---|
| Always predict on time | 29.4 min |
| Each train's usual delay at that station | 27.2 min |
| LightGBM | **24.6 min** |

The middle row is the real baseline. Just remembering how late a train normally is at a
station already does well, so the model only counts if it beats that. It does, by about
10%. 67% of predictions are within 15 minutes, and the "up to" range covers 87% of actual
delays (it aims for 90).

Features: the train's own history at that station, the station's average, distance from
origin, stop number, station traffic, zone, hour, weekday and train type. History is
computed from the training days only, so nothing leaks from the test week.

The biggest error is in long delays. Most arrivals are within 15 minutes but there's a tail
of 2 hour plus delays that nobody predicts well from a timetable. That's why the app shows
a range and not one number.

### Weather in the model

The model doesn't use weather yet. I wrote `scripts/fetch_weather_history.py` to pull
hourly rain, wind and storm data for September 2024 from the free Open-Meteo archive and
join it to each arrival, but I couldn't run it from my dev setup. Running it and retraining
with `--weather` adds those features, and the admin page will show whether they helped.
I tested the pipeline with random weather, and as expected it added nothing (24.88 vs
24.85), so the join itself works.

Until then the app is honest about it: the passenger page says the delay comes from the
model, and the weather is shown next to it as a separate thing.

## Is the weather real?

With `OWM_API_KEY` set, yes. The backend calls OpenWeatherMap for each station's
coordinates, caches each 0.25 degree grid cell for 10 minutes, and takes the 3-hour slot
closest to when the train reaches that stop.

Without a key it runs in demo mode and every page says "demo data". Demo weather is
generated per region and day (coast, north plains, north-east, interior) so neighbouring
stations agree with each other and the same search gives the same answer. If a key is set
but the API is down, it falls back to demo weather and says that too.

Forecasts only go 5 days ahead. Trips further out show the date the forecast becomes
available instead of made-up weather.

## Data

| What | Source | Licence |
|---|---|---|
| Stations, track links, train routes, 1.28M delay records (Sep 2024) | [RSTGCN dataset](https://github.com/KoyenaChowdhury/RSTGCN), IIT Kharagpur | none stated, cited below |
| Station coordinates | [datameet/railways](https://github.com/datameet/railways) (2016) | CC0 |
| Historical weather (optional) | [Open-Meteo archive](https://open-meteo.com/) | CC BY 4.0 |
| Live weather | OpenWeatherMap | API key |

None of the data is committed. `scripts/build_data.py` downloads it and builds
`data/processed/`. Cleaning it took longer than the model:

- RSTGCN has no coordinates, so they come from datameet. About 20 stations had been
  renamed since 2016 (Mughal Sarai is now Pt Deen Dayal Upadhyaya Jn, DDU instead of MGS),
  so there's an alias table. 269 stations still had no location and are placed between
  their neighbours on the line.
- 343 trains had placeholder timetables (every stop at 00:00). For 331 I rebuilt the
  times from the scheduled times in the delay file; the other 106 trains are dropped.
- Run days aren't in the route file, so they're worked out from which weekdays each train
  shows up in the delay data.

If you use the RSTGCN data, please cite the paper:

> Koyena Chowdhury, Paramita Koley, Abhijnan Chakraborty, Saptarshi Ghosh. *RSTGCN:
> Railway-centric spatio-temporal graph convolutional network for train delay
> prediction.* IEEE Transactions on Intelligent Transportation Systems, 2026.
> [arXiv:2510.01262](https://arxiv.org/abs/2510.01262)

## Running it

Backend (Python 3.10 or newer, tested on 3.11 and 3.14). I use `python -m pip` and
`python -m uvicorn` instead of plain `pip` and `uvicorn` because on some Windows laptops
the security settings block the small `pip.exe` and `uvicorn.exe` launchers.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt

python scripts/build_data.py         # downloads and cleans the data
python scripts/train_delay_model.py  # a minute or two

export OWM_API_KEY=your_key          # optional, leave it out for demo weather
export JWT_SECRET=any-long-random-string
python -m uvicorn backend.main:app --reload
```

Optional, to add weather to the model:

```bash
python scripts/fetch_weather_history.py
python scripts/train_delay_model.py --weather data/raw/weather_sep2024.csv
```

The API runs on http://localhost:8000 with Swagger docs at `/docs`. On first start it
creates `test.db` and an admin account (`admin` / `admin123`). Change that before deploying
anywhere.

If you skip `build_data.py` the app still runs on the old 17-city sample network, and if
you skip the model it falls back to the weather rules for delays.

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. If the backend is somewhere else, set `VITE_API_BASE`.

Tests:

```bash
python -m pip install pytest
python -m pytest -q
```

There are three test files:

- `tests/test_route_planner.py` checks the planner on the small sample network, so it's
  fast and always gives the same answer.
- `tests/test_api.py` runs the whole app through FastAPI's test client: sign-up and OTP,
  who can call which endpoint, train search, the route planner, saved trips (including
  that one user can't see or delete another's) and admin password resets. It uses its
  own throwaway database, so it never touches your `test.db`.
- `tests/test_real_data.py` checks the real network and the model, and skips itself if
  you haven't built them.

Four API tests are marked `xfail`. They're security holes I know about and haven't fixed
yet: no minimum password length, unlimited OTP guesses, `/admin/users` sends password
hashes, and CORS allows any site. They show up
in every test run so they don't get forgotten.

Other settings: `WEATHER_CACHE_TTL` (seconds, default 600), `FRONTEND_ORIGINS` for CORS,
and the `SMTP_*` variables in `backend/email_utils.py` for OTP emails. Without SMTP the OTP
is printed on screen.

## API

| Method | Path | What it returns |
|---|---|---|
| GET | `/user/stations?q=` | Station search, city groups first |
| GET | `/user/train-search` | Trains between two stations or cities on a date, best first. Query: `source`, `destination`, `travel_date` |
| GET | `/user/trains` | Timetable search with paging. Query: `q`, `limit`, `offset` |
| GET | `/user/journey-forecast` | Forecast and predicted delay for one train. Query: `train_number`, `travel_date`, optional `source` and `destination` |
| GET | `/user/tickets/{id}/forecast` | Same thing for a saved trip |
| POST | `/admin/weather-route` | Alternative routes with the forecast at each stop and the reasons. Body: `source`, `destination`, optional `departure` and `k` |
| GET | `/admin/model` | Test-week results for the delay model |
| GET | `/admin/weather/{code}` | Current weather and 5-day forecast for one station |
| GET | `/admin/weather-overview` | Weather and delay risk at the 20 busiest stations |
| GET | `/admin/network` | Stations and track links for the map |
| POST | `/admin/users/{id}/reset-password` | Admin sets a new password. Body: `new_password` |

The original endpoints (`/auth/*`, `/admin/shortest-route`, `/admin/optimization-chart`)
still work.

## Project layout

```
scripts/
  build_data.py           downloads and cleans the rail data
  train_delay_model.py    LightGBM delay model and its test report
  fetch_weather_history.py  Sep 2024 weather from Open-Meteo
backend/
  network.py              loads the network, station search, trains between stations
  route_planner.py        alternative routes, delay rules, explanations, train search
  delay_model.py          loads the trained model and predicts per stop
  weather.py              OpenWeatherMap client, cache, demo forecasts
  cities.py               city groups (Hyderabad = SC, HYB, KCG, LPI) and display names
  dijkstra.py             the original shortest path
  sample_data.py          the old 17-city network, used by tests and as a fallback
  routers/                auth, user and admin endpoints
frontend/src/
  pages/                  one file per screen
  components/             NetworkMap, StationPicker, StopStrip, JourneyForecast
tests/
```

## Limitations

- The timetables are from September 2024. Some trains have changed since, so the app tells
  people to check times on IRCTC.
- Track links are station to station with straight lines on the map, not the real track
  shape.
- The weather to delay rules in the route planner are my own numbers, not fitted to data.
  The passenger side uses the model, the planner still uses the rules, because the model
  needs a real train number and the planner works with routes, not trains.
- One month of data. Monsoon and fog season behave differently, so a model trained on
  September will be off in December.

Vansh Rana, 2026
