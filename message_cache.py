from collections import defaultdict, OrderedDict

class MessageCache:
    def __init__(self, max_size=10000):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.deleted_cache = defaultdict(OrderedDict)
        self.update_cache = defaultdict(OrderedDict)

    def add(self, message):
        message_id = message['id']
        channel_id = message['channel_id']
        self.cache[message_id] = {'message': message, 'channel_id': channel_id}
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)


    def update(self, message):
        message_id = message['id']
        channel_id = message['channel_id']

        if message_id in self.cache:
            old_message = self.cache[message_id]['message']

            if channel_id in self.update_cache and message_id in self.update_cache[channel_id]:
                if self.update_cache[channel_id][message_id][-1]['content'] != old_message['content']:
                    self.update_cache[channel_id][message_id].append(old_message)
            else:
                self.update_cache[channel_id][message_id] = [old_message]

            self.cache[message_id] = {'message': message, 'channel_id': channel_id}


    def delete(self, message_id):
        if message_id in self.cache:
            deleted_message = self.cache[message_id]['message']
            channel_id = self.cache[message_id]['channel_id']

            self.deleted_cache[channel_id][message_id] = deleted_message

            del self.cache[message_id]

    def get(self, message_id):
        if message_id in self.cache:
            return self.cache[message_id]['message']


    def get_deleted(self, channel_id):
        """Retrieve the last deleted message for a specific channel."""
        if channel_id in self.deleted_cache and self.deleted_cache[channel_id]:
            last_deleted_message_id = list(self.deleted_cache[channel_id].keys())[-1]
            return self.deleted_cache[channel_id][last_deleted_message_id]
        return None


    def get_updates(self, channel_id):
        """Retrieve the last updated message for a specific channel."""
        if channel_id in self.update_cache and self.update_cache[channel_id]:
            last_updated_message_id = list(self.update_cache[channel_id].keys())[-1]
            return self.update_cache[channel_id][last_updated_message_id]
        return None


class ReactionCache:
    def __init__(self, max_size=10000):
        self.max_size = max_size
        self.cache = OrderedDict()
    
    def add(self, user_id, user_info):
        self.cache[user_id] = user_info
        # If the cache is full, remove the oldest reaction
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
    
    def get(self, user_id):
        return self.cache.get(user_id)