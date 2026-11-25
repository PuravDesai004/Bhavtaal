# MolBhaav

MolBhaav is a mobile-first voice bargaining game built with FastAPI, SQLite, vanilla JavaScript, and Google's Gemini API. It supports spoken or typed offers, deterministic price movement, daily arenas and leaderboards, and shareable deal receipts.

## Run locally

From the `molbhaav` directory, create an environment and install the pinned dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

On macOS or Linux, use `python3 -m venv .venv`, then `.venv/bin/python -m pip install -r requirements.txt` and `.venv/bin/python main.py`.

Open `http://127.0.0.1:8000`. The server binds to `0.0.0.0`; set `PORT` to change the port. By default, SQLite data and local audio files go under `./local_data`. Set `DATA_DIR` to choose another data directory.

## Configuration

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Enables Gemini turn analysis, debriefs, and generated voice. Without it, the app uses its built-in deterministic conversation fallback and browser speech. |
| `DATA_DIR` | SQLite and local audio directory; defaults to `./local_data`. |
| `PORT` | HTTP listen port; defaults to `8000`. |
| `STORAGE_URL` and `STORAGE_TOKEN` | Enable Embarko file storage for generated boss-reaction WAVs. With either value absent, audio uses local storage. |
| `APP_NAME` | Embarko storage app name; defaults to `molbhaav`. |
| `CRON_SECRET` | Required bearer token for the daily archive route. Embarko schedules provide this secret to scheduled requests. |

User microphone recordings are processed for the current turn and are not written to disk. The app stores negotiation text and deal data in SQLite. It saves only generated boss-reaction audio, when available.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Health and configuration status. |
| `GET` | `/api/arenas` | Today's public arena data. |
| `POST` | `/api/session/start` | Start an arena session. |
| `POST` | `/api/session/sample-audio` | Request the boss greeting audio. |
| `POST` | `/api/turn` | Submit a typed or recorded offer. |
| `POST` | `/api/session/finish` | Lock the current result and create a deal receipt. |
| `GET` | `/api/leaderboard?arena_id=daily_market` | Daily leaderboard for `daily_market`; all-time leaderboards for `placement_hr` and `freelance_client`. |
| `GET` | `/api/deal/{deal_id}` | Deal data for the receipt view. |
| `GET` | `/api/local-audio/{deal_id}` | Local generated reaction audio when the app uses local storage. |
| `GET` | `/deal/{deal_id}` | Shareable HTML receipt page. |
| `GET` | `/api/internal/rotate-daily` | Archive yesterday's daily results; requires `Authorization: Bearer $CRON_SECRET`. |

Interactive API documentation is available at `/docs` while the server is running.

## Tests

Run the deterministic pricing and API tests with:

```powershell
python -m pytest -q
```

## Embarko deployment checklist

1. Deploy the `molbhaav` directory as the app root, including `main.py`, `requirements.txt`, `embarko.json`, and the `static`, `tests`, and Python module files.
2. Add `GEMINI_API_KEY` as an app secret to enable Gemini features. Leave it unset to use the deterministic fallback.
3. Add `STORAGE_URL` and `STORAGE_TOKEN` if generated voice clips should use Embarko file storage. The app keeps no user-recorded audio there.
4. Confirm the deployed service has a durable writable `DATA_DIR` for SQLite, and set that variable if the platform's writable path differs from `./local_data`.
5. Deploy and check `/api/health`, `/api/arenas`, and `/docs`. A health response of `"storage_mode":"local"` means the storage credentials were not detected; `"gemini_configured":true` means the Gemini key is present.
6. Confirm the daily schedule from `embarko.json` is active and that Embarko supplies `CRON_SECRET` in its bearer authorization header. The scheduled GET route and manual POST route both require that authorization.
7. After the first deployment assigns the app an ID, add that ID as `appId` in `embarko.json` if Embarko requests or recommends it.

The scheduled archive uses midnight in `Asia/Kolkata`. Embarko's schedule format and bearer authentication are documented in its [schedules guide](https://embarko.ai/docs/schedules); the manifest shape is in the [`embarko.json` reference](https://embarko.ai/docs/embarko-json). Hosted file uploads and deletion use Embarko's [file storage API](https://embarko.ai/docs/files).
