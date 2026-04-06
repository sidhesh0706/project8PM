def compute_error_rate(failed_requests, total_requests):
    try:
        return failed_requests / total_requests
    except TypeError:
        return 0.0