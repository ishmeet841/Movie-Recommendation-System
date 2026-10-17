import streamlit as st
import pickle
import pandas as pd
import requests
import os
from pathlib import Path

# ========================
# CONFIGURATION
# ========================
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"
PLACEHOLDER_IMAGE = "https://via.placeholder.com/500x750?text=No+Image"
MOVIES_PER_PAGE = 10
MOVIES_PER_ROW = 5
TMDB_TIMEOUT_SECONDS = 10
BASE_DIR = Path(__file__).resolve().parent
MOVIES_PATH = BASE_DIR / "movies.pkl"
SIMILARITY_PATH = BASE_DIR / "similarity.pkl"


def get_api_key():
    api_key = None
    try:
        api_key = st.secrets.get("TMDB_API_KEY")
    except Exception:
        pass

    if not api_key:
        api_key = os.getenv("TMDB_API_KEY")

    return api_key.strip() if isinstance(api_key, str) and api_key.strip() else None


def show_status_once(message_key, level, message):
    if st.session_state.get(message_key):
        return

    st.session_state[message_key] = True
    getattr(st, level)(message)


API_KEY = get_api_key()

st.set_page_config(page_title="🎬 Movie Recommender", layout="wide")

# ========================
# API FUNCTIONS
# ========================
def fetch_poster(movie_id):
    """Fetch poster image URL from TMDB API."""
    if not API_KEY:
        return PLACEHOLDER_IMAGE

    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    try:
        response = requests.get(
            url,
            params={"api_key": API_KEY, "language": "en-US"},
            timeout=TMDB_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        poster_path = data.get("poster_path")
        return f"{POSTER_BASE_URL}{poster_path}" if poster_path else PLACEHOLDER_IMAGE
    except requests.Timeout:
        show_status_once(
            "tmdb_timeout_warning_shown",
            "warning",
            "TMDB poster request timed out. Showing placeholders where poster data is unavailable.",
        )
        return PLACEHOLDER_IMAGE
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        if status_code in (401, 403):
            show_status_once(
                "tmdb_auth_warning_shown",
                "warning",
                "TMDB poster request was rejected (401/403). Verify TMDB_API_KEY in Streamlit secrets.",
            )
        else:
            show_status_once(
                "tmdb_http_warning_shown",
                "warning",
                f"TMDB poster request failed (HTTP {status_code}). Showing placeholders where needed.",
            )
        return PLACEHOLDER_IMAGE
    except (requests.RequestException, ValueError):
        show_status_once(
            "tmdb_fetch_warning_shown",
            "warning",
            "TMDB poster lookup is temporarily unavailable. Showing placeholders where poster data is unavailable.",
        )
        return PLACEHOLDER_IMAGE

# ========================
# RECOMMENDATION LOGIC
# ========================
def recommend(movie):
    """Return recommended movie titles and poster URLs, including the searched movie."""
    movie_index = movies[movies['title'] == movie].index[0]
    distances = similarity[movie_index]
    movies_list = sorted(
        enumerate(distances),
        reverse=True,
        key=lambda x: x[1]
    )[:51]  # Get top 51 similar movies (including the searched movie)

    names, posters = [], []

    # Get details for the searched movie itself
    searched_movie_id = movies.iloc[movie_index].movie_id
    names.append(movies.iloc[movie_index].title)
    posters.append(fetch_poster(searched_movie_id))

    # Add recommendations (excluding the first one, which is the searched movie itself)
    for idx, _ in movies_list:
        if idx != movie_index: # Skip the searched movie from the recommendations list
            movie_id = movies.iloc[idx].movie_id
            names.append(movies.iloc[idx].title)
            posters.append(fetch_poster(movie_id))
    return names, posters


def load_movies(path):
    with path.open("rb") as movie_file:
        movies_obj = pickle.load(movie_file)
    return movies_obj if isinstance(movies_obj, pd.DataFrame) else pd.DataFrame(movies_obj)


def load_similarity(path):
    with path.open("rb") as similarity_file:
        return pickle.load(similarity_file)


def build_similarity(movies_df):
    if "tags" not in movies_df.columns:
        raise ValueError(
            "Missing 'tags' column in movies.pkl, so similarity.pkl cannot be generated automatically."
        )

    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vectors = CountVectorizer(max_features=5000, stop_words="english").fit_transform(
        movies_df["tags"].fillna("")
    )
    similarity_matrix = cosine_similarity(vectors)

    try:
        with SIMILARITY_PATH.open("wb") as similarity_file:
            pickle.dump(similarity_matrix, similarity_file)
    except OSError:
        pass

    return similarity_matrix


# ========================
# LOAD DATA
# ========================
if not MOVIES_PATH.exists():
    st.error(f"Missing required data file: {MOVIES_PATH.name}")
    st.stop()

try:
    movies = load_movies(MOVIES_PATH)
except Exception as exc:
    st.error(f"Unable to load {MOVIES_PATH.name}: {exc}")
    st.stop()

try:
    similarity = load_similarity(SIMILARITY_PATH) if SIMILARITY_PATH.exists() else build_similarity(movies)
except Exception as exc:
    st.error(
        "Unable to load or build similarity matrix. "
        "Ensure movies.pkl includes a 'tags' column or provide similarity.pkl."
    )
    st.caption(f"Details: {exc}")
    st.stop()

if not API_KEY:
    st.warning("TMDB_API_KEY is not configured. Posters will use placeholders.")
    st.info(
        "Add this in Streamlit Cloud **App settings → Secrets**:\n\n"
        "```toml\nTMDB_API_KEY = \"your_tmdb_api_key\"\n```\n\n"
        "After saving, redeploy/restart the app. For local/alternate deployments, you can also set the "
        "`TMDB_API_KEY` environment variable."
    )

# CUSTOM STYLING
# ========================
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(to bottom, #0f2027, #203a43, #2c5364);
        color: white;
        font-family: 'Segoe UI', sans-serif;
    }
    .movie-card {
        text-align: center;
        padding: 10px;
        border-radius: 10px;
        background-color: rgba(255, 255, 255, 0.05);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .movie-card:hover {
        transform: scale(1);
        box-shadow: 0px 4px 20px rgba(255,255,255,0.3);
    }
    .movie-title {
        font-size: 16px;
        font-weight: bold;
        color: white;
        margin-top: 8px;
    }
    div[data-testid="column"] {
        padding: 0px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ========================
# HEADER
# ========================
st.markdown("<h1 style='text-align: center; color: white;'>🎥 Movie Recommender System</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: white;'>Find your next favorite movie!</p>", unsafe_allow_html=True)

# ========================
# MOVIE SELECTION BAR
# ========================
col1, col2 = st.columns([6, 1])
with col1:
    selected_movie_name = st.selectbox("", movies['title'].values, label_visibility="collapsed")
with col2:
    recommend_clicked = st.button("🎯 Recommend", use_container_width=True)

# ========================
# SESSION STATE INIT
# ========================
if "page" not in st.session_state:
    st.session_state.page = 1
if "names" not in st.session_state:
    st.session_state.names = []
    st.session_state.posters = []

# ========================
# HANDLE RECOMMENDATION
# ========================
if recommend_clicked:
    st.session_state.names, st.session_state.posters = recommend(selected_movie_name)
    st.session_state.page = 1  # Reset to first page

# ========================
# SHOW RECOMMENDATIONS
# ========================
if st.session_state.names:
    total_pages = (len(st.session_state.names) + MOVIES_PER_PAGE - 1) // MOVIES_PER_PAGE

    # Pagination controls
    col_prev, _, col_next = st.columns([1, 8, 1])
    with col_prev:
        if st.button("⬅ Previous", use_container_width=True, disabled=(st.session_state.page == 1)):
            st.session_state.page -= 1
    with col_next:
        if st.button("Next ➡", use_container_width=True, disabled=(st.session_state.page == total_pages)):
            st.session_state.page += 1

    # Current page movies
    start_idx = (st.session_state.page - 1) * MOVIES_PER_PAGE
    end_idx = start_idx + MOVIES_PER_PAGE
    page_names = st.session_state.names[start_idx:end_idx]
    page_posters = st.session_state.posters[start_idx:end_idx]

    # Display movie grid
    for row_start in range(0, len(page_names), MOVIES_PER_ROW):
        cols = st.columns(MOVIES_PER_ROW)
        for idx, col in enumerate(cols):
            movie_idx = row_start + idx
            if movie_idx < len(page_names):
                with col:
                    st.markdown(f"""
                        <div class="movie-card">
                            <img src="{page_posters[movie_idx]}" width="80%" style="border-radius: 10px;">
                            <div class="movie-title">{page_names[movie_idx]}</div>
                        </div>
                    """, unsafe_allow_html=True)