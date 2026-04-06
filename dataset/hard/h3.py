def normalize_headers(headers):
    return {key.lower(): value.strip() for key, value in headers.items()}