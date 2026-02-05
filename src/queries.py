def userListQuery(mediaType, chunk):
    return f"""query MediaListCollection($name: String) {{
    MediaListCollection (userName: $name, type: {mediaType}, status_not: PLANNING, chunk: {chunk}, perChunk: 60) {{
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
                }}
              }}
            }}
          }}
        }}
      }}
    }}
  }}"""


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
