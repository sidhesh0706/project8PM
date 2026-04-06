def read_file(filename):
    base_dir = "/var/www/uploads/"
    filepath = base_dir + filename
    with open(filepath, 'r') as f:
        return f.read()