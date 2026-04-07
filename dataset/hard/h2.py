def read_file(path):
    try:
        f = open(path, 'r')
        return f.read()
    except:
        return None