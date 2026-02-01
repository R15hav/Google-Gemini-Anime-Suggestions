
# Anime Suggestions

Lightweight service that generates personalized anime recommendations by combining Anilist data with a large language model (Google Gemini).

## Overview

- Backend: `backend/` contains the recommendation logic and service glue.
- Frontend: `frontend/` contains a simple UI (Streamlit) to interact with the backend.
- Services: `backend/services/` contains integrations for AniList and Gemini.

## Features

- Fetch candidate anime from AniList by genre/tag.
- Analyze user watch history and produce curated recommendations using Gemini.
- Configurable model and API keys via environment variables.

## Requirements

- Python 3.10+
- Recommended: virtualenv or venv

Install dependencies (project uses pyproject.toml):

```bash
uv init
```

If you use `pyproject.toml` tooling (Poetry/Flit), follow your normal workflow.

## Configuration (.env)

Create a `.env` file in the project root (same directory as this README). Example:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

Notes:
- The backend loads environment variables using `python-dotenv` so `.env` is automatically read.
- Keep API keys secret and add `.env` to `.gitignore`.

## Running the Backend

Start the backend service (example):

```bash
cd backend
uvicorn main:app --reload
```

`backend/main.py` is the entry point that wires together `backend/services/gemini.py` and `backend/services/anilist.py`.

## Running the Frontend

The frontend is a Streamlit app. From the project root:

```bash
cd frontend
streamlit run app.py
```

The frontend communicates with the backend to fetch recommendations and display them.

## Services

- `backend/services/anilist.py`: Minimal AniList GraphQL client used to fetch candidate anime and user lists.
- `backend/services/gemini.py`: Wraps calls to Google Gemini. Configure `GEMINI_API_KEY` and optionally `GEMINI_MODEL`.

## Contributing

Feel free to open issues or PRs. For changes affecting prompts or model usage, please include rationale and examples.

## License

This repository does not include a license file. Add one if you plan to publish this project.

