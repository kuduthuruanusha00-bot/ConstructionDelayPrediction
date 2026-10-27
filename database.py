
import sqlite3


def create_database():
    connection = sqlite3.connect("database.db")
    connection.execute("PRAGMA foreign_keys = ON")
    cursor = connection.cursor()

    # USERS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            team_member_id INTEGER
        )
    """)

    # Add the column to an existing database if it is missing
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]

    if "team_member_id" not in columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN team_member_id INTEGER"
        )

    # One login account per team-member profile
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_users_team_member_id
        ON users(team_member_id)
        WHERE team_member_id IS NOT NULL
    """)

    # Default accounts (existing accounts are preserved)
    users = [
        ("admin", "admin123", "admin"),
        ("projectmanager", "PM@12345", "manager"),
        ("member", "member123", "member")
    ]

    for user in users:
        try:
            cursor.execute("""
                INSERT INTO users (username, password, role)
                VALUES (?, ?, ?)
            """, user)
        except sqlite3.IntegrityError:
            pass

    # PROJECTS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            description TEXT NOT NULL,
            start_date TEXT NOT NULL,
            deadline TEXT NOT NULL,
            location TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    # TASKS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            task_name TEXT NOT NULL,
            resource TEXT NOT NULL,
            deadline TEXT NOT NULL,
            progress INTEGER NOT NULL,
            dependency TEXT,
            FOREIGN KEY (project_id)
                REFERENCES projects(id)
                ON DELETE CASCADE
        )
    """)

    # RESOURCES TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            resource_name TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            utilization INTEGER NOT NULL,
            FOREIGN KEY (project_id)
                REFERENCES projects(id)
                ON DELETE CASCADE
        )
    """)

    # TEAM MEMBERS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            member_name TEXT NOT NULL,
            responsibility TEXT NOT NULL,
            task_id INTEGER,
            deadline TEXT,
            progress INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (project_id)
                REFERENCES projects(id)
                ON DELETE CASCADE,
            FOREIGN KEY (task_id)
                REFERENCES tasks(id)
                ON DELETE SET NULL
        )
    """)

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_database()
    print("Database created successfully!")
