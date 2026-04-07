def get_user_by_id(db, user_id: int):
    """
    Secure query path using parameterized SQL.
    """
    query = "SELECT id, email, role FROM users WHERE id = ?"
    return db.execute(query, (user_id,)).fetchone()
