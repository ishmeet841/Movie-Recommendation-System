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

### Required secret

Add this in **App settings → Secrets**:

```toml
TMDB_API_KEY = "your_tmdb_api_key"
```

If `TMDB_API_KEY` is missing, the app still runs but movie posters use a placeholder image.

### Model/data files

- `movies.pkl` is loaded from the repository root relative to `app.py`.
- If `similarity.pkl` exists, it is loaded.
- If `similarity.pkl` is missing, the app generates the similarity matrix at startup from the `tags` column in `movies.pkl` (same CountVectorizer + cosine similarity approach used in the notebook) and then attempts to save `similarity.pkl`.

This avoids startup crashes on Streamlit Cloud when `similarity.pkl` is not committed.
