import os
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st


# ============================================================
# APP CONFIG
# ============================================================

st.set_page_config(
    page_title="News Intelligence Dashboard",
    page_icon="🗞️",
    layout="wide",
    initial_sidebar_state="expanded",
)

NEWS_ENDPOINT = "https://newsapi.org/v2/top-headlines"


# ============================================================
# CONSTANTS
# ============================================================

COUNTRIES = {
    "India": "in",
    "United States": "us",
    "United Kingdom": "gb",
    "Australia": "au",
    "Canada": "ca",
    "Singapore": "sg",
    "United Arab Emirates": "ae",
    "Germany": "de",
    "France": "fr",
    "Japan": "jp",
    "South Korea": "kr",
    "China": "cn",
    "Brazil": "br",
    "South Africa": "za",
}

CATEGORIES = [
    "general",
    "business",
    "technology",
    "science",
    "health",
    "sports",
    "entertainment",
]


# ============================================================
# HELPERS
# ============================================================

def get_api_key() -> str:
    """
    Reads the NewsAPI key from Streamlit secrets first,
    then from environment variables.
    """
    try:
        return st.secrets["NEWSAPI_KEY"]
    except Exception:
        return os.getenv("NEWSAPI_KEY", "")


def safe_get_source(article: dict) -> str:
    source = article.get("source") or {}
    return source.get("name") or "Unknown source"


def format_date(date_string: str) -> str:
    if not date_string:
        return "Unknown date"

    try:
        dt = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return date_string


def get_domain(url: str) -> str:
    if not url:
        return ""

    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


@st.cache_data(ttl=600, show_spinner=False)
def fetch_news(api_key: str, params: dict) -> dict:
    """
    Fetches news from NewsAPI.

    Caching prevents burning through the free API quota on every Streamlit rerun.
    """
    headers = {
        "X-Api-Key": api_key
    }

    response = requests.get(
        NEWS_ENDPOINT,
        headers=headers,
        params=params,
        timeout=15,
    )

    try:
        data = response.json()
    except Exception:
        raise RuntimeError("NewsAPI returned a non-JSON response.")

    if response.status_code != 200 or data.get("status") == "error":
        message = data.get("message", "Unknown API error.")
        code = data.get("code", response.status_code)
        raise RuntimeError(f"{code}: {message}")

    return data


def articles_to_dataframe(articles: list[dict]) -> pd.DataFrame:
    rows = []

    for article in articles:
        rows.append(
            {
                "title": article.get("title"),
                "source": safe_get_source(article),
                "author": article.get("author"),
                "published_at": article.get("publishedAt"),
                "description": article.get("description"),
                "url": article.get("url"),
                "image_url": article.get("urlToImage"),
                "domain": get_domain(article.get("url")),
            }
        )

    return pd.DataFrame(rows)


def render_article_card(article: dict, index: int) -> None:
    title = article.get("title") or "Untitled article"
    description = article.get("description") or "No description available."
    source = safe_get_source(article)
    author = article.get("author") or "Unknown author"
    published_at = format_date(article.get("publishedAt"))
    url = article.get("url")
    image_url = article.get("urlToImage")
    domain = get_domain(url)

    with st.container(border=True):
        left, right = st.columns([1, 3], vertical_alignment="top")

        with left:
            if image_url:
                st.image(image_url, use_container_width=True)
            else:
                st.info("No image")

        with right:
            st.subheader(f"{index}. {title}")
            st.caption(f"{source} · {domain} · {published_at}")
            st.write(description)

            meta_col_1, meta_col_2 = st.columns(2)
            with meta_col_1:
                st.write(f"**Author:** {author}")
            with meta_col_2:
                st.write(f"**Source:** {source}")

            if url:
                st.link_button("Read full article", url)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🧭 Filters")

api_key = get_api_key()

if not api_key:
    st.sidebar.error("Missing NewsAPI key.")
    st.sidebar.write(
        "Add your key to `.streamlit/secrets.toml` as `NEWSAPI_KEY`."
    )

selected_country_name = st.sidebar.selectbox(
    "Location",
    options=list(COUNTRIES.keys()),
    index=list(COUNTRIES.keys()).index("India"),
)

selected_category = st.sidebar.selectbox(
    "Topic",
    options=CATEGORIES,
    index=0,
)

keyword = st.sidebar.text_input(
    "Search keyword",
    placeholder="e.g., AI, elections, cricket, startups",
)

num_articles = st.sidebar.slider(
    "Number of articles",
    min_value=5,
    max_value=100,
    value=20,
    step=5,
)

page = st.sidebar.number_input(
    "Page",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
)

search_within_results = st.sidebar.text_input(
    "Search within fetched results",
    placeholder="Filter displayed cards locally",
)

fetch_button = st.sidebar.button(
    "Fetch headlines",
    type="primary",
    use_container_width=True,
)

clear_cache_button = st.sidebar.button(
    "Clear cache",
    use_container_width=True,
)

if clear_cache_button:
    st.cache_data.clear()
    st.sidebar.success("Cache cleared.")


# ============================================================
# MAIN UI
# ============================================================

st.title("🗞️ News Intelligence Dashboard")
st.write(
    "Fetch top headlines from NewsAPI and filter them by location, topic, article count, and keywords."
)

with st.expander("How this app works"):
    st.markdown(
        """
        This app sends a request to the NewsAPI `top-headlines` endpoint using:

        - `country` for location
        - `category` for topic
        - `q` for keyword search
        - `pageSize` for number of articles
        - `page` for pagination

        The API key is passed through the `X-Api-Key` request header.
        """
    )


# ============================================================
# FETCH AND DISPLAY NEWS
# ============================================================

if fetch_button:
    if not api_key:
        st.error("Cannot fetch news because the API key is missing.")
        st.stop()

    params = {
        "country": COUNTRIES[selected_country_name],
        "category": selected_category,
        "pageSize": num_articles,
        "page": page,
    }

    if keyword.strip():
        params["q"] = keyword.strip()

    with st.spinner("Fetching headlines..."):
        try:
            data = fetch_news(api_key=api_key, params=params)
        except Exception as e:
            st.error("Could not fetch news.")
            st.exception(e)
            st.stop()

    articles = data.get("articles", [])
    total_results = data.get("totalResults", 0)

    df = articles_to_dataframe(articles)

    if search_within_results.strip() and not df.empty:
        local_query = search_within_results.strip().lower()

        mask = (
            df["title"].fillna("").str.lower().str.contains(local_query)
            | df["description"].fillna("").str.lower().str.contains(local_query)
            | df["source"].fillna("").str.lower().str.contains(local_query)
            | df["author"].fillna("").str.lower().str.contains(local_query)
        )

        df = df[mask]

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)

    metric_1.metric("API total results", total_results)
    metric_2.metric("Displayed articles", len(df))
    metric_3.metric("Country", selected_country_name)
    metric_4.metric("Topic", selected_category.title())

    if df.empty:
        st.warning("No articles found for these filters.")
        st.stop()

    st.divider()

    tab_cards, tab_table, tab_export = st.tabs(
        ["Article cards", "Data table", "Export"]
    )

    with tab_cards:
        filtered_articles = df.to_dict("records")

        for i, article in enumerate(filtered_articles, start=1):
            normalized_article = {
                "title": article.get("title"),
                "description": article.get("description"),
                "author": article.get("author"),
                "publishedAt": article.get("published_at"),
                "url": article.get("url"),
                "urlToImage": article.get("image_url"),
                "source": {
                    "name": article.get("source")
                },
            }

            render_article_card(normalized_article, i)

    with tab_table:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

    with tab_export:
        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download results as CSV",
            data=csv,
            file_name="newsapi_headlines.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.json(
            {
                "endpoint": NEWS_ENDPOINT,
                "params_used": params,
                "total_results": total_results,
                "displayed_results": len(df),
            }
        )

else:
    st.info("Choose filters in the sidebar and click **Fetch headlines**.")