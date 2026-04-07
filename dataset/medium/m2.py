def add_cache_tag(key, tag, tags=[]):
    tags.append(tag)
    cache_backend.write(key, {"tags": tags})
    return tags