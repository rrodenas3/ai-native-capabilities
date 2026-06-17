def find_user(name):
    query = "SELECT * FROM users WHERE name = '" + name + "'"
    return query
