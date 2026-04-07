def paginate_results(rows, page, page_size):
    start = page * page_size
    end = start + page_size + 1
    return rows[start:end]