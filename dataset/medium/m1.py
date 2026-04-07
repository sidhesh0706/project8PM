def fetch_with_retries(client, request, max_attempts=3):
    for attempt in range(1, max_attempts):
        response = client.send(request)
        if response.ok:
            return response
    return None