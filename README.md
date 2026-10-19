# Movie-Recommendation-System

Streamlit movie recommender using content-based filtering.

## Local run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud deployment

Use these settings in Streamlit Cloud:

- **Main file path**: `app.py`
- **Requirements file**: `requirements.txt`

### TMDB secret configuration (Streamlit Cloud)

In Streamlit Cloud open **Manage app → Settings → Secrets**, then add:

```toml
TMDB_API_KEY = "your_tmdb_api_key"
```

You can alternatively use a TMDB v4 read access token:

```toml
TMDB_BEARER_TOKEN = "your_tmdb_v4_read_access_token"
```

Save the secret, then **redeploy/restart** the app so the new value is loaded.

Do **not** reuse the previously exposed TMDB key; generate and use a new key.

For local or alternate deployments, you can also set:

```bash
export TMDB_API_KEY="your_tmdb_api_key"
export TMDB_BEARER_TOKEN="your_tmdb_v4_read_access_token"
```

Supported variable names are `TMDB_API_KEY`, `TMDB_BEARER_TOKEN`, and `TMDB_V4_ACCESS_TOKEN`.

If `TMDB_API_KEY` is missing or invalid, the app still runs but movie posters use placeholder images.

### Model/data files

- `movies.pkl` is loaded from the repository root relative to `app.py`.
- If `similarity.pkl` exists, it is loaded.
- If `similarity.pkl` is missing, the app generates the similarity matrix at startup from the `tags` column in `movies.pkl` (same CountVectorizer + cosine similarity approach used in the notebook) and then attempts to save `similarity.pkl`.

This avoids startup crashes on Streamlit Cloud when `similarity.pkl` is not committed.
