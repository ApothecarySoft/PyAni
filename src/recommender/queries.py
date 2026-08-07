user_list_query_minimal = """
    query MediaListCollection($name: String, $type: MediaType, $chunk: Int) {
        MediaListCollection (userName: $name, type: $type, status_not: PLANNING, chunk: $chunk, perChunk: 20) {
            hasNextChunk
            lists {
                name
                isCustomList
                entries {
                    score(format: POINT_100)
                    media {
                        id
                    }
                }
            }
        }
    }
"""

media_query = """
    query Media(id: $id) {
        id
        type
        title {
            english
            userPreferred
        }
        staff (page: 1, perPage: 20, sort: FAVOURITES_DESC) {
            nodes {
                id
                name {
                    userPreferred
                }
            }
        }
        meanScore
        format
        popularity
        startDate {
            year
        }
        studios (isMain: true) {
            nodes {
                name
                id
            }
        }
        genres
        tags {
            id
            rank
            name
        }
        coverImage {
            medium
        }
        recommendations (sort: RATING_DESC) {
            nodes {
                rating
                mediaRecommendation {
                    id
                }
            }
        }
    }
"""

def user_list_query():
    return f"""query MediaListCollection($name: String, $type: MediaType, $chunk: Int) {{
    MediaListCollection (userName: $name, type: $type, status_not: PLANNING, chunk: $chunk, perChunk: 20) {{
      hasNextChunk
      lists {{
        name
        isCustomList
        entries {{
          score(format: POINT_100)
          status
          media {{
            id
            title {{
              english
              userPreferred
            }}
            staff (page: 1, perPage: 20, sort: FAVOURITES_DESC) {{
              nodes {{
                id
                name {{
                  userPreferred
                }}
              }}
            }}
            meanScore
            popularity
            startDate {{
              year
            }}
            studios (isMain: true) {{
              nodes {{
                name
                id
              }}
            }}
            genres
            tags {{
              id
              rank
              name
            }}
            recommendations (sort: RATING_DESC) {{
              nodes {{
                rating
                mediaRecommendation {{
                  id
                  type
                  title {{
                    english
                    userPreferred
                  }}
                  staff (page: 1, perPage: 20, sort: FAVOURITES_DESC) {{
                    nodes {{
                      id
                      name {{
                        userPreferred
                      }}
                    }}
                  }}
                  meanScore
                  format
                  popularity
                  startDate {{
                    year
                  }}
                  studios (isMain: true) {{
                    nodes {{
                      name
                      id
                    }}
                  }}
                  genres
                  tags {{
                    id
                    rank
                    name
                  }}
                  coverImage {{
                    medium
                  }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
  }}"""


hunter_query = """
query($status: [MediaStatus], $sort: [MediaSort], $tag: String, $page: Int) {
  Page(page: $page) {
    pageInfo {
      hasNextPage
    }
    media(status_in: $status, sort: $sort, tag: $tag) {
      id
      type
      format
      coverImage {
        medium
      }
      title {
        english
        userPreferred
      }
      tags {
        id
        name
        rank
      }
    }
  }
}
"""


# def userMeanScoresQuery():
#     return f"""query User($name: String) {{
#   User (name: $name) {{
#     statistics {{
#       anime {{
#         meanScore
#       }}
#       manga {{
#         meanScore
#       }}
#     }}
#   }}
# }}"""


# def userQuery(username, pageNum, mediaType):
#     return f"""query {{\n
#                   Page(page: {pageNum}) {{\n
#                     users(name: \"{username}\") {{\n
#                       id\n
#                       statistics {{\n
#                         {mediaType} {{\n
#                           scores (sort: MEAN_SCORE_DESC) {{\n
#                             score\n
#                             mediaIds\n
#                           }}\n
#                         }}\n
#                       }}\n
#                     }}\n
#                   }}\n
#                 }}"""


# def animeQuery(id):
#     return f"""query {{
#         Media (id: {id}) {{
#             title {{
#                 english
#                 userPreferred
#             }}
#             meanScore
#             popularity
#             seasonYear
#             isAdult
#             description
#             studios {{
#                 nodes {{
#                     name
#                     id
#                 }}
#             }}
#             genres
#             tags {{
#                 id
#                 rank
#                 name
#             }}
#             recommendations {{
#                 nodes {{
#                     rating
#                     mediaRecommendation {{
#                         title {{
#                             english
#                             userPreferred
#                         }}
#                         meanScore
#                         id
#                         popularity
#                         seasonYear
#                         isAdult
#                         description
#                         studios {{
#                             nodes {{
#                                 name
#                                 id
#                             }}
#                         }}
#                         genres
#                         tags {{
#                             id
#                             rank
#                             name
#                         }}
#                     }}
#                 }}
#             }}
#         }}
#     }}"""
