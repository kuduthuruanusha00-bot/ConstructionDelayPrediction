
import sqlite3

connection = sqlite3.connect("database.db")
connection.row_factory = sqlite3.Row

print("\n--- TEAM MEMBERS ---")
members = connection.execute("""
    SELECT id, member_name, project_id
    FROM team_members
    ORDER BY id
""").fetchall()

for member in members:
    print(
        f"Member ID: {member['id']} | "
        f"Name: {member['member_name']} | "
        f"Project ID: {member['project_id']}"
    )

print("\n--- EXISTING LOGIN ACCOUNTS ---")
users = connection.execute("""
    SELECT id, username, role, team_member_id
    FROM users
    ORDER BY id
""").fetchall()

for user in users:
    print(
        f"User ID: {user['id']} | "
        f"Username: {user['username']} | "
        f"Role: {user['role']} | "
        f"Team Member ID: {user['team_member_id']}"
    )

connection.close()
