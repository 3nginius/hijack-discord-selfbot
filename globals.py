global user_data, global_token, relationship_counts, detailed_relationships

user_data = {}

relationship_counts = {
    'friends': 0,
    'blocked': 0,
    'incoming_requests': 0,
    'outgoing_requests': 0
}

detailed_relationships = {
    'friends': [],
    'blocked': [],
    'incoming_requests': [],
    'outgoing_requests': []
}