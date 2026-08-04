from prompts import query_parsing


def query_retreive(query,vectorstore) :

    parsed_query = query_parsing(query)
    return vectorstore.invoke(parsed_query)