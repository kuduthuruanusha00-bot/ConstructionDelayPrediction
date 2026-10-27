from flask import Flask, render_template, request, session, redirect, url_for
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "construction_delay_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")


def get_connection():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def check_role(roles):
    return session.get("role") in roles


def password_matches(stored, entered):
    if not stored:
        return False
    if stored.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(stored, entered)
    return stored == entered  # supports the existing starter accounts


@app.route("/")
def home():
    return render_template("login.html")



@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "").strip()

    if not username or not password or not role:
        return "Please enter username, password, and role."

    db = get_connection()

    columns = {
        r["name"] for r in db.execute("PRAGMA table_info(users)")
    }

    if "team_member_id" not in columns:
        db.close()
        return "team_member_id is missing. Run database.py first."

    user = db.execute(
        """SELECT id, username, password, role, team_member_id
           FROM users WHERE username = ?""",
        (username,)
    ).fetchone()

    db.close()

    if (
        not user
        or user["role"] != role
        or not password_matches(user["password"], password)
    ):
        return "Invalid username, password, or role."

    # Check that a member account is linked to a profile
    if role == "member" and not user["team_member_id"]:
        return (
            "Your login is not linked to a team-member profile. "
            "Ask your Project Manager to create an account for your profile."
        )

    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    session["team_member_id"] = user["team_member_id"]

    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    elif role == "manager":
        return redirect(url_for("manager_dashboard"))
    elif role == "member":
        return redirect(url_for("member_dashboard"))

    return "Invalid role."


@app.route("/admin-dashboard")
def admin_dashboard():
    if not check_role(["admin"]):
        return "Access Denied. Admin access required."
    return render_template("admin_dashboard.html", username=session.get("username"))


@app.route("/manager-dashboard")
def manager_dashboard():
    if not check_role(["manager"]):
        return "Access Denied. Project Manager access required."
    return render_template("manager_dashboard.html", username=session.get("username"))


@app.route("/member-dashboard")
def member_dashboard():
    if not check_role(["member"]):
        return "Access Denied. Member access required."
    member_id = session.get("team_member_id")
    if not member_id:
        return ("Your login is not linked to a team-member profile. "
                "Ask your Project Manager to create an account for your profile.")
    db = get_connection()
    member = db.execute("""
        SELECT tm.id, tm.member_name, tm.responsibility, tm.progress, tm.deadline,
               p.project_name, t.task_name, t.progress AS task_progress,
               t.deadline AS task_deadline
        FROM team_members tm
        JOIN projects p ON p.id=tm.project_id
        LEFT JOIN tasks t ON t.id=tm.task_id
        WHERE tm.id=?
    """, (member_id,)).fetchone()
    db.close()
    if member is None:
        return "Your team-member profile could not be found."
    return render_template("member_dashboard.html",
                           username=session.get("username"), member=member)


@app.route("/project")
def project():
    if not check_role(["manager"]):
        return "Access Denied. Only Project Manager can create projects."
    return render_template("project.html")


@app.route("/create-project", methods=["POST"])
def create_project():
    if not check_role(["manager"]):
        return "Access Denied."
    name = request.form.get("project_name", "").strip()
    if not name:
        return "Project name is required."
    values = (name, request.form.get("description", ""),
              request.form.get("start_date") or None,
              request.form.get("deadline") or None,
              request.form.get("location", ""),
              request.form.get("status", "Not Started"))
    db = get_connection()
    db.execute("""INSERT INTO projects
        (project_name, description, start_date, deadline, location, status)
        VALUES (?, ?, ?, ?, ?, ?)""", values)
    db.commit()
    db.close()
    return redirect(url_for("projects"))


@app.route("/projects")
def projects():
    if not check_role(["admin", "manager", "member"]):
        return "Access Denied."
    db = get_connection()
    rows = db.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()
    db.close()
    return render_template("projects.html", projects=rows, role=session.get("role"))


@app.route("/delete-project/<int:project_id>")
def delete_project(project_id):
    if not check_role(["manager"]):
        return "Access Denied. Only Project Manager can delete projects."
    db = get_connection()
    # Explicit deletes also support older databases without cascade rules.
    db.execute("DELETE FROM team_members WHERE project_id=?", (project_id,))
    db.execute("DELETE FROM tasks WHERE project_id=?", (project_id,))
    db.execute("DELETE FROM resources WHERE project_id=?", (project_id,))
    db.execute("DELETE FROM projects WHERE id=?", (project_id,))
    db.commit()
    db.close()
    return redirect(url_for("projects"))


@app.route("/tasks")
def tasks():
    if not check_role(["manager"]):
        return "Access Denied. Only Project Manager can manage tasks."
    db = get_connection()
    rows = db.execute("SELECT id, project_name FROM projects ORDER BY id DESC").fetchall()
    db.close()
    return render_template("tasks.html", projects=rows)


@app.route("/create-task", methods=["POST"])
def create_task():
    if not check_role(["manager"]):
        return "Access Denied."
    project_id = request.form.get("project_id", type=int)
    name = request.form.get("task_name", "").strip()
    progress = request.form.get("progress", default=0, type=int)
    if not project_id or not name:
        return "Please select a project and enter a task name."
    if progress is None or not 0 <= progress <= 100:
        return "Progress must be between 0 and 100."
    db = get_connection()
    if not db.execute("SELECT id FROM projects WHERE id=?", (project_id,)).fetchone():
        db.close()
        return "Selected project does not exist."
    db.execute("""INSERT INTO tasks
        (project_id, task_name, resource, deadline, progress, dependency)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (project_id, name, request.form.get("resource", ""),
         request.form.get("deadline") or None, progress,
         request.form.get("dependency", "")))
    db.commit()
    db.close()
    return redirect(url_for("stored_tasks"))


@app.route("/stored-tasks")
def stored_tasks():
    if not check_role(["admin", "manager", "member"]):
        return "Access Denied."
    db = get_connection()
    rows = db.execute("""
        SELECT tasks.id, projects.project_name, tasks.task_name, tasks.resource,
               tasks.deadline, tasks.progress, tasks.dependency
        FROM tasks JOIN projects ON tasks.project_id=projects.id
        ORDER BY tasks.id DESC
    """).fetchall()
    db.close()
    return render_template("stored_tasks.html", tasks=rows)


@app.route("/resources")
def resources():
    if not check_role(["manager"]):
        return "Access Denied. Only Project Manager can manage resources."
    db = get_connection()
    rows = db.execute("SELECT id, project_name FROM projects ORDER BY id DESC").fetchall()
    db.close()
    return render_template("resources.html", projects=rows)


@app.route("/resource-recommendation")
def resource_recommendation():
    if not check_role(["manager"]):
        return "Access Denied. Only Project Manager can view recommendations."

    db = get_connection()

    resources = db.execute("""
        SELECT resources.id,
               projects.project_name,
               resources.resource_name,
               resources.resource_type,
               resources.quantity,
               resources.utilization
        FROM resources
        JOIN projects ON resources.project_id = projects.id
        ORDER BY resources.utilization ASC,
                 resources.quantity DESC
    """).fetchall()

    db.close()

    recommendations = []

    for resource in resources:
        quantity = resource["quantity"] or 0
        utilization = resource["utilization"] or 0

        if quantity <= 0:
            status = "Unavailable"
            advice = "Check the quantity before assigning this resource."
        elif utilization <= 70:
            status = "Recommended"
            advice = "Some resource capacity is available."
        else:
            status = "Limited availability"
            advice = "Check alternatives or scheduling."

        recommendations.append({
            "project_name": resource["project_name"],
            "resource_name": resource["resource_name"],
            "resource_type": resource["resource_type"],
            "quantity": quantity,
            "utilization": utilization,
            "status": status,
            "advice": advice
        })

    return render_template(
        "resource_recommendation.html",
        recommendations=recommendations
    )


@app.route("/create-resource", methods=["POST"])
def create_resource():
    if not check_role(["manager"]):
        return "Access Denied."
    project_id = request.form.get("project_id", type=int)
    name = request.form.get("resource_name", "").strip()
    quantity = request.form.get("quantity", type=int)
    utilization = request.form.get("utilization", type=int)
    if not project_id or not name:
        return "Please select a project and enter a resource name."
    if quantity is None or quantity < 0:
        return "Quantity must be zero or greater."
    if utilization is None or not 0 <= utilization <= 100:
        return "Utilization must be between 0 and 100."
    db = get_connection()
    if not db.execute("SELECT id FROM projects WHERE id=?", (project_id,)).fetchone():
        db.close()
        return "Selected project does not exist."
    db.execute("""INSERT INTO resources
        (project_id, resource_name, resource_type, quantity, utilization)
        VALUES (?, ?, ?, ?, ?)""",
        (project_id, name, request.form.get("resource_type", ""), quantity, utilization))
    db.commit()
    db.close()
    return redirect(url_for("stored_resources"))


@app.route("/stored-resources")
def stored_resources():
    if not check_role(["admin", "manager", "member"]):
        return "Access Denied."
    db = get_connection()
    rows = db.execute("""
        SELECT resources.id, projects.project_name, resources.resource_name,
               resources.resource_type, resources.quantity, resources.utilization
        FROM resources JOIN projects ON resources.project_id=projects.id
        ORDER BY resources.id DESC
    """).fetchall()
    db.close()
    return render_template("stored_resources.html", resources=rows)


@app.route("/processed-data")
def processed_data():
    if not check_role(["manager"]):
        return "Access Denied. Only Project Manager can view processed data."
    from data_processing import process_project_data
    return render_template("processed_data.html", data=process_project_data())


@app.route("/delay-risk")
def delay_risk():
    if not check_role(["manager"]):
        return "Access Denied. Only Project Manager can view delay risk."
    from data_processing import process_project_data
    from ml_model import predict_risk
    results = []
    for item in process_project_data():
        risk = predict_risk(progress=item["progress"],
                            days_remaining=item["days_remaining"],
                            dependency=1 if item["dependency"] else 0,
                            utilization=item["utilization"])
        results.append({**item, "risk": risk})
    return render_template("delay_risk.html", results=results)


@app.route("/analytics")
def analytics():
    if not check_role(["admin", "manager"]):
        return "Access Denied. Only Admin or Project Manager can view analytics."
    db = get_connection()
    total_projects = db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    total_tasks = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    avg_progress = db.execute("SELECT COALESCE(AVG(progress),0) FROM tasks").fetchone()[0]
    avg_util = db.execute("SELECT COALESCE(AVG(utilization),0) FROM resources").fetchone()[0]
    completed = db.execute("SELECT COUNT(*) FROM tasks WHERE progress=100").fetchone()[0]
    pending = db.execute("SELECT COUNT(*) FROM tasks WHERE progress<100").fetchone()[0]
    db.close()
    from data_processing import process_project_data
    from ml_model import predict_risk
    risk_counts = {"Low": 0, "Medium": 0, "High": 0}
    for item in process_project_data():
        risk = predict_risk(progress=item["progress"],
                            days_remaining=item["days_remaining"],
                            dependency=1 if item["dependency"] else 0,
                            utilization=item["utilization"])
        if risk in risk_counts:
            risk_counts[risk] += 1
    return render_template("analytics.html", total_projects=total_projects,
        total_tasks=total_tasks, average_progress=round(avg_progress, 2),
        average_utilization=round(avg_util, 2), completed_tasks=completed,
        pending_tasks=pending, low_risk=risk_counts["Low"],
        medium_risk=risk_counts["Medium"], high_risk=risk_counts["High"])


@app.route("/risk-alerts")
def risk_alerts():
    if not check_role(["manager"]):
        return "Access Denied. Only Project Manager can view risk alerts."
    from data_processing import process_project_data
    from ml_model import predict_risk
    alerts = []
    for item in process_project_data():
        risk = predict_risk(progress=item["progress"],
                            days_remaining=item["days_remaining"],
                            dependency=1 if item["dependency"] else 0,
                            utilization=item["utilization"])
        if risk == "High":
            recommendation = "Immediate attention required. Review task progress, dependencies, and resources."
        elif risk == "Medium":
            recommendation = "Monitor the task closely and consider additional resources if required."
        else:
            continue
        alerts.append({**item, "risk": risk, "recommendation": recommendation})
    return render_template("risk_alerts.html", alerts=alerts)


@app.route("/update-project-status")
def update_project_status():
    if not check_role(["manager"]):
        return "Access Denied. Only Project Manager can update status."
    db = get_connection()
    projects_rows = db.execute("SELECT id FROM projects").fetchall()
    for p in projects_rows:
        avg = db.execute("SELECT COALESCE(AVG(progress),0) FROM tasks WHERE project_id=?",
                         (p["id"],)).fetchone()[0]
        status = "Complete" if avg == 100 else ("In Progress" if avg > 0 else "Not Started")
        db.execute("UPDATE projects SET status=? WHERE id=?", (status, p["id"]))
    db.commit()
    db.close()
    return redirect(url_for("manager_dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/team-members", methods=["GET", "POST"])
def team_members():
    if not check_role(["manager"]):
        return "Access Denied. Only Project Manager can manage team members."
    db = get_connection()
    if request.method == "POST":
        project_id = request.form.get("project_id", type=int)
        name = request.form.get("member_name", "").strip()
        responsibility = request.form.get("responsibility", "").strip()
        task_id = request.form.get("task_id", type=int)
        deadline = request.form.get("deadline", "").strip()
        if not project_id or not name or not responsibility:
            db.close()
            return "Please provide a project, member name, and responsibility."
        if not db.execute("SELECT id FROM projects WHERE id=?", (project_id,)).fetchone():
            db.close()
            return "Selected project does not exist."
        if task_id and not db.execute(
            "SELECT id FROM tasks WHERE id=? AND project_id=?", (task_id, project_id)
        ).fetchone():
            db.close()
            return "Please select a task belonging to this project."
        db.execute("""INSERT INTO team_members
            (project_id, member_name, responsibility, task_id, deadline)
            VALUES (?, ?, ?, ?, ?)""", (project_id, name, responsibility, task_id, deadline or None))
        db.commit()
        db.close()
        return redirect(url_for("team_members"))

    projects_data = db.execute("SELECT id, project_name FROM projects ORDER BY id DESC").fetchall()
    tasks_data = db.execute("SELECT id, project_id, task_name FROM tasks ORDER BY id DESC").fetchall()
    members = db.execute("""
        SELECT tm.id, tm.project_id, tm.task_id, tm.member_name, tm.responsibility,
               tm.deadline, tm.progress, p.project_name, t.task_name
        FROM team_members tm JOIN projects p ON tm.project_id=p.id
        LEFT JOIN tasks t ON tm.task_id=t.id ORDER BY tm.id DESC
    """).fetchall()
    db.close()
    return render_template("team_members.html", projects=projects_data,
                           tasks=tasks_data, members=members)


@app.route("/create-member-account/<int:member_id>", methods=["POST"])
def create_member_account(member_id):
    if not check_role(["manager"]):
        return "Access Denied. Only the Project Manager can create accounts."
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or len(password) < 8:
        return "Enter a username and a password with at least 8 characters."

    db = get_connection()
    columns = {r["name"] for r in db.execute("PRAGMA table_info(users)")}
    if "team_member_id" not in columns:
        db.close()
        return "users.team_member_id is missing. Stop the app and run 'python database.py'."
    if not db.execute("SELECT id FROM team_members WHERE id=?", (member_id,)).fetchone():
        db.close()
        return "Team member not found."
    if db.execute("SELECT id FROM users WHERE team_member_id=?", (member_id,)).fetchone():
        db.close()
        return "This team member already has a login account."
    try:
        db.execute("""INSERT INTO users (username, password, role, team_member_id)
                      VALUES (?, ?, 'member', ?)""",
                   (username, generate_password_hash(password), member_id))
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        db.close()
        return "That username already exists. Please choose another."
    db.close()
    return redirect(url_for("team_members"))


@app.route("/update-member-progress/<int:member_id>", methods=["POST"])
def update_member_progress(member_id):
    if not check_role(["manager", "member"]):
        return "Access Denied."
    progress = request.form.get("progress", type=int)
    if progress is None or not 0 <= progress <= 100:
        return "Progress must be between 0 and 100."

    db = get_connection()
    member = db.execute("SELECT project_id, task_id FROM team_members WHERE id=?",
                        (member_id,)).fetchone()
    if member is None:
        db.close()
        return "Team member not found."
    if session.get("role") == "member" and session.get("team_member_id") != member_id:
        db.close()
        return "Access Denied. You can update only your own progress."

    db.execute("UPDATE team_members SET progress=? WHERE id=?", (progress, member_id))
    if member["task_id"] is not None:
        db.execute("UPDATE tasks SET progress=? WHERE id=? AND project_id=?",
                   (progress, member["task_id"], member["project_id"]))
    db.commit()
    db.close()
    if session.get("role") == "manager":
        return redirect(url_for("team_members"))
    return redirect(url_for("member_dashboard"))


@app.route("/assign-member-task/<int:member_id>", methods=["POST"])
def assign_member_task(member_id):
    if not check_role(["manager"]):
        return "Access Denied. Only Project Manager can assign tasks."
    task_id = request.form.get("task_id", type=int)
    if not task_id:
        return "Please select a task."
    db = get_connection()
    member = db.execute("SELECT id, project_id, progress FROM team_members WHERE id=?",
                        (member_id,)).fetchone()
    if member is None:
        db.close()
        return "Team member not found."
    task = db.execute("""SELECT id, project_id, deadline FROM tasks
                         WHERE id=? AND project_id=?""",
                      (task_id, member["project_id"])).fetchone()
    if task is None:
        db.close()
        return "Select a task from the team member's project."
    db.execute("UPDATE team_members SET task_id=?, deadline=? WHERE id=?",
               (task["id"], task["deadline"], member_id))
    db.execute("UPDATE tasks SET progress=? WHERE id=? AND project_id=?",
               (member["progress"], task_id, member["project_id"]))
    db.commit()
    db.close()
    return redirect(url_for("team_members"))


if __name__ == "__main__":
    app.run(debug=True)
