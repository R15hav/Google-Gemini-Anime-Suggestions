import requests

ANILIST_URL = "https://graphql.anilist.co"
SEARCH_QUERY = """
query ($genre: String, $tag: String, $page: Int) {
  Page (page: $page, perPage: 20) {
    media (genre: $genre, tag: $tag, sort: SCORE_DESC, type: ANIME, isAdult: false) {
      title { english romaji }
      genres
      description
      averageScore
    }
  }
}
"""

def fetch_candidates(genre: str = None, tag: str = None):
    # We randomize the page number to ensure variety in results
    import random
    page = random.randint(1, 5) 
    
    variables = {"page": page}
    if genre: variables["genre"] = genre
    if tag: variables["tag"] = tag
        
    response = requests.post(ANILIST_URL, json={'query': SEARCH_QUERY, 'variables': variables})
    return response.json().get('data', {}).get('Page', {}).get('media', [])

def fetch_user_watchlist(username: str):
    query = """
            query ($name: String) {
            MediaListCollection(userName: $name, type: ANIME, status_in: [COMPLETED, DROPPED]) {
                lists {
                status
                entries {
                    score(format: POINT_10)
                    media {
                    title { english romaji }
                    genres
                    tags { name }
                    description
                    }
                }
                }
            }
            }
            """
    response = requests.post(ANILIST_URL, json={'query': query, 'variables': {'name': username}})
    return response.json()