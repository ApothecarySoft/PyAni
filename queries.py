userListQuery = """query {\n
                    Page(page: 1) {\n
                    mediaList(userName: \"9tailedfaux\", type: ANIME, sort: SCORE_DESC, status: COMPLETED) {\n
                      media {\n
                        title {\n
                          userPreferred\n
                        }\n
                        status\n
                        format\n
                        seasonYear\n
                        episodes\n
                        popularity\n
                        score\n
                        recommendations {\n
                          edges {\n
                            node {\n
                              rating\n
                              mediaRecommendation {\n
                                id\n
                                title {\n
                                  userPreferred\n
                                }\n
                              }\n
                            }\n
                          }\n
                        }\n
                      }\n
                    }\n
                    pageInfo {\n
                      hasNextPage\n
                    }\n
                  }\n
                }"""

def userQuery(username, pageNum):
    return f"""query {{\n  
                  Page(page: {pageNum}) {{\n  
                    users(name: \"{username}\") {{\n  
                      id\n  
                      statistics {{\n  
                        anime {{\n  
                          scores (sort: MEAN_SCORE_DESC) {{\n  
                            score\n  
                            mediaIds\n  
                          }}\n  
                        }}\n  
                      }}\n  
                    }}\n  
                  }}\n  
                }}"""
