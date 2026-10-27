import sqlite3
from datetime import datetime

DATABASE = "database.db"


def process_project_data():

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            tasks.id,
            projects.project_name,
            tasks.task_name,
            tasks.deadline,
            tasks.progress,
            tasks.dependency,
            COALESCE(resources.utilization, 50)
        FROM tasks
        JOIN projects
        ON tasks.project_id = projects.id
        LEFT JOIN resources
        ON tasks.project_id = resources.project_id
    """)

    tasks = cursor.fetchall()

    processed_data = []

    today = datetime.today().date()

    for task in tasks:

        task_id = task[0]
        project_name = task[1]
        task_name = task[2]
        deadline = task[3]
        progress = task[4]
        dependency = task[5]
        utilization = task[6]

        remaining_progress = 100 - progress

        try:
            deadline_date = datetime.strptime(
                deadline,
                "%Y-%m-%d"
            ).date()

            days_remaining = (
                deadline_date - today
            ).days

        except ValueError:
            days_remaining = 0

        if days_remaining < 0 and progress < 100:
            delay_indicator = 1

        elif days_remaining <= 7 and progress < 70:
            delay_indicator = 1

        else:
            delay_indicator = 0

        processed_data.append({
            "task_id": task_id,
            "project_name": project_name,
            "task_name": task_name,
            "progress": progress,
            "remaining_progress": remaining_progress,
            "days_remaining": days_remaining,
            "dependency": dependency,
            "utilization": utilization,
            "delay_indicator": delay_indicator
        })

    connection.close()

    return processed_data


if __name__ == "__main__":

    data = process_project_data()

    print("\n===== PROCESSED PROJECT DATA =====\n")

    for item in data:

        print("Task ID:", item["task_id"])
        print("Project:", item["project_name"])
        print("Task:", item["task_name"])
        print("Progress:", item["progress"], "%")
        print("Remaining Progress:",
              item["remaining_progress"], "%")
        print("Days Remaining:",
              item["days_remaining"])
        print("Dependency:",
              item["dependency"])
        print("Resource Utilization:",
              item["utilization"], "%")
        print("Delay Indicator:",
              item["delay_indicator"])

        print("--------------------------------")