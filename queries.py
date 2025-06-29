def userListQuery(userName, type):
  return f"""query MediaListCollection {{
    MediaListCollection (userName: "{userName}", type: {type}, status_not: PLANNING) {{
      hasNextChunk
      lists {{
        name
        entries {{
          score(format: POINT_100)
          media {{
            id
            title {{
              english
              userPreferred
            }}
            meanScore
            popularity
            seasonYear
            isAdult
            description
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
            recommendations {{
              nodes {{
                rating
                mediaRecommendation {{
                  id
                  title {{
                    english
                    userPreferred
                  }}
                  meanScore
                  format
                  id
                  popularity
                  seasonYear
                  isAdult
                  description
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

def userMeanScoresQuery(username):
  return f"""query User {{
  User (name: "{username}") {{
    statistics {{
      anime {{
        meanScore
      }}
      manga {{
        meanScore
      }}
    }}
  }}
}}"""

def userQuery(username, pageNum, mediaType):
    return f"""query {{\n  
                  Page(page: {pageNum}) {{\n  
                    users(name: \"{username}\") {{\n  
                      id\n  
                      statistics {{\n  
                        {mediaType} {{\n  
                          scores (sort: MEAN_SCORE_DESC) {{\n  
                            score\n  
                            mediaIds\n  
                          }}\n  
                        }}\n  
                      }}\n  
                    }}\n  
                  }}\n  
                }}"""

def animeQuery(id):
    return f"""query {{
        Media (id: {id}) {{
            title {{
                english
                userPreferred
            }}
            meanScore
            popularity
            seasonYear
            isAdult
            description
            studios {{
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
            recommendations {{
                nodes {{
                    rating
                    mediaRecommendation {{
                        title {{
                            english
                            userPreferred
                        }}
                        meanScore
                        id
                        popularity
                        seasonYear
                        isAdult
                        description
                        studios {{
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
    }}"""