import os
import json
import sqlite3
import random
import math
import string
from flask import Flask, redirect, render_template, session, request, jsonify
from re import fullmatch, sub
from werkzeug.security import generate_password_hash, check_password_hash
from helpers import *
from copy import deepcopy

app = Flask(__name__)

DATA_DIRECTORY = "data"

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

try:
    con = sqlite3.connect(f"{DATA_DIRECTORY}/mathemastery.db", check_same_thread=False)
    db = con.cursor()
    print("Successfully connected to database")
except sqlite3.Error as e:
    print(f"Error connecting to database")
    raise 

units = None
with open("data/topics.json", "r") as f:
    units = json.load(f)

if units is None:
    print("Error in loading topics data")
    raise
else:
    print("Successfully loaded topics data")

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
def root():
    if session.get("user_id"):
        id = session.get("user_id")

        _info = db.execute("SELECT display FROM users WHERE id = ?", (id,)).fetchone()
        if not db.execute("SELECT * FROM mastery WHERE user_id = ?", (id,)).fetchone():
            info = {
                "display": _info[0],
                "learned": 0,
                "masteries": 0,
                "accuracy": 0,
                "total_time": "0 minutes"
            }
        else:
            acc = db.execute("SELECT SUM(correct), SUM(total) FROM mastery WHERE user_id = ?", (id,)).fetchone()

            info = {
                "display": _info[0],
                "learned": db.execute("SELECT COUNT(*) FROM mastery WHERE user_id = ?", (id,)).fetchone()[0],
                "masteries": db.execute("SELECT COUNT(*) FROM mastery WHERE user_id = ? AND progress = 100", (id,)).fetchone()[0],
                "total_time": int_to_time(math.floor(db.execute("SELECT SUM(time) FROM mastery WHERE user_id = ?", (id,)).fetchone()[0] / 60)),
            }
            if acc[1] == 0:
                info["accuracy"] = 0
            else:
                info["accuracy"] = round(acc[0] / acc[1], 1)
        return render_template("home.html", info=info)
    else:
        return render_template("overview.html")

@app.route("/login", methods=["GET", "POST"])
@login_prohibitied
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        info = request.form

        username = info.get("username")
        password = info.get("password")

        pass_hash = db.execute("SELECT hash, id FROM users WHERE username = ?", (username,)).fetchone()
        
        if not pass_hash or not check_password_hash(pass_hash[0], password):
            return render_template("login.html", message="Username or password did not match.")

        session["user_id"] = pass_hash[1]
        session["username"] = username
        
        return redirect("/")
        

@app.route("/register", methods=["GET", "POST"])
@login_prohibitied
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        info = request.form

        username = info.get("username")        
        password = info.get("password")
        name = info.get("name")
        confirm = info.get("confirm")

        if not username:
            return render_template("register.html", message="No username was provided.")      
        if not password:
            return render_template("register.html", message="No password was provided.")
        if not name:
            return render_template("register.html", message="No display name was provided.")

        if confirm != password:
            return render_template("register.html", message="Password and confirmation did not match.")
        if fullmatch(r"^(?=.{4,16}$)(?![_.])(?!.*[_.]{2})[a-zA-Z0-9._]+(?<![_.])$", username) is None:
            return render_template("register.html", message="Username must be between 4 and 16 alphanumeric characters long. It can also include underscores and periods, but cannot end in one of these or have two of these consecutively.")
        if fullmatch(r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$", password) is None:
            return render_template("register.html", message="Password must have at least 8 characters, with at least one letter, number, and special character.")
        
        hash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash, display) VALUES (?,?,?)", (username, hash, name))
        con.commit()

        session["user_id"] = db.lastrowid
        session["username"] = username

        return redirect("/")
    
@app.route("/logout")
@login_required
def logout():
    session.clear()

    return redirect("/")

@app.route("/topics")
def topics():
    level_separated = {}

    for topic in units:
        t = deepcopy(topic)

        mastery = get_topic_mastery(session.get("user_id"), topic["id"])

        t["mastery"] = mastery[0]

        if topic["level"] not in list(level_separated.keys()):
            level_separated[topic["level"]] = [t]
        
        else:
            level_separated[topic["level"]].append(t)
    
    return render_template("topics.html", levels=level_separated)

@app.route("/topic/<id>")
def topic_page(id):
    topic = None

    for t in units:
        if t["id"] == int(id):
            topic = deepcopy(t)
            break
    
    if topic is None:
        return render_template("error.html", error=[404, "The topic URL provided could not be found."])

    mastery = get_topic_mastery(session.get("user_id"), topic["id"])
    
    topic["started"] = not mastery == [0,0,0,0]
    topic["progress"] = mastery[0]
    topic["time"] = int_to_time(math.trunc(mastery[1] / 60))
    topic["sample"] = generate_problem(t)
    topic["learns"] = db.execute("SELECT COUNT(*) FROM mastery WHERE topic_id = ?", (topic["id"],)).fetchone()[0]
    topic["masteries"] = db.execute("SELECT COUNT(*) FROM mastery WHERE topic_id = ? AND progress = 100", (t["id"],)).fetchone()[0]
    try:
        topic["total_time"] = int_to_time(math.trunc(db.execute("SELECT SUM(time) FROM mastery WHERE topic_id = ?", (t["id"],)).fetchone()[0] / 60))
    except:
        topic["total_time"] = int_to_time(0)
    
    if mastery[3] == 0:
        topic["acc"] = None
    else:
        topic["acc"] = round(mastery[2] / mastery[3], 1)

    teacher = True
    classes = []
    if session.get("user_id") is None:
        teacher = False
    else:
        cls = db.execute("SELECT id, name FROM classrooms WHERE teacher_id = ?", (session.get("user_id"),)).fetchall()
        if cls is None:
            teacher = False
        for cl in cls:
            classes.append({
                "id": cl[0],
                "name": cl[1]
            })

    return render_template("topic.html", topic=topic, teacher=teacher, classes=classes)

@app.route("/learn/<id>")
def learn(id):
    topic = None

    for t in units:
        if t["id"] == int(id):
            topic = deepcopy(t)
            break
    
    if topic is None:
        return render_template("error.html", error=[404, "The topic provided could not be found"])
    
    m = get_topic_mastery(session.get("user_id"), topic["id"])
    topic["progress"] = m[0]
    topic["time"] = m[1]
    
    return render_template("learn.html", topic=topic)

@app.route("/classroom/<id>", methods=["GET"])
@login_required
def classroom(id):
    class_info = db.execute("SELECT name, teacher_id, join_code FROM classrooms WHERE id = ?", (id,)).fetchone()
    user = session.get("user_id")
    
    if class_info is None:
        return render_template("error.html", error=[404, "Classroom could not be found."])
    
    teacher = user == class_info[1]

    if db.execute("SELECT * FROM taken WHERE user_id = ? AND classroom_id = ?", (user, id)).fetchone() is None and not teacher:
        return render_template("error.html", error=[400, "You do not have permission to view this classroom"])
    
    _assignments = db.execute("SELECT id, topic_id FROM assignments WHERE classroom_id = ?", (id,)).fetchall()
    assignments = []

    for assignment in _assignments:
        for unit in units:
            if unit["id"] == assignment[1]:
                info = {
                    "id": assignment[0],
                    "topic": unit["topic"]
                }

                if not teacher:
                    info["topic_id"] = assignment[1]
                    info["topic_progress"] = get_topic_mastery(user, assignment[1])[0]

                assignments.append(info)
    
    classroom = {
        "name": class_info[0],
        "join_code": class_info[2],
        "id": id
    }

    return render_template("classroom.html", classroom=classroom, assignments=assignments, teacher=teacher)



@app.route("/classrooms", methods=["GET", "POST"])
def classrooms():
    id = session.get("user_id")

    if id is not None:
        taught, taken= get_classrooms(id)
    else:
        if request.method == 'GET':
            return render_template("classrooms.html", taken=[], taught=[])
        else:
            return render_template("classrooms.html", taken=[], taught=[], message="You must be logged in to create a classroom.")

    if request.method == "POST":      
        name = request.form.get("name").strip()

        if len(name) < 4 or len(name) > 40:
            return render_template("classrooms.html", taken=taken, taught=taught, message="Classroom name must be between 4 and 40 characters long.")

        db.execute("INSERT INTO classrooms (teacher_id, name, join_code) VALUES (?, ?, ?)", (id, name, ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))))
        con.commit()

        return redirect("/classrooms")
    else:
        return render_template("classrooms.html", taken=taken, taught=taught)

@app.route("/assign/<id>", methods=["POST"])
@login_required
def assign(id):
    exists = False

    for unit in units:
        if unit["id"] == int(id):
            exists = True
            break
    
    if not exists:
        return render_template("error.html", error=[404, "Topic to assign could not be found."])

    class_id = request.form.get("class_id")
    if class_id is None:
        return render_template("error.html", error=[404, "Class could not be found"])
    
    if db.execute("SELECT * FROM classrooms WHERE teacher_id = ? and id = ?", (session.get("user_id"),class_id)).fetchone() is None:
        return redirect(f"/topic/{id}")
    if db.execute("SELECT * FROM assignments WHERE topic_id = ? and classroom_id = ?", (id, class_id)).fetchone() is not None:
        return render_template("error.html", error=[400, "This topic is already assigned to this classroom."])
    
    db.execute("INSERT INTO assignments (topic_id, classroom_id) VALUES (?,?)", (id, class_id))
    con.commit()

    return redirect(f"/topic/{id}")

@app.route("/joinclassroom", methods=["POST"])
def joinclassroom():
    id = session.get("user_id")

    if id is None:
        return render_template("classrooms.html", taught=[], taken=[], joinMessage="You must be logged in to join a classroom.")
    
    req = request.form

    class_id = req.get("classId")
    join_code = req.get("joinCode")

    taught, taken = get_classrooms(id)

    if class_id is None or join_code is None:
        return render_template("classrooms.html", taught=taught, taken=taken, joinMessage="Invalid class ID or join code inputted.")
    
    if db.execute("SELECT id, teacher_id FROM classrooms WHERE id = ? AND teacher_id = ?", (class_id, id)).fetchone() is not None:
        return render_template("classrooms.html", taught=taught, taken=taken, joinMessage="Teachers cannot be enrolled in their own class.")
    
    verify = db.execute("SELECT * FROM classrooms WHERE id = ? AND join_code = ?", (class_id, join_code.upper())).fetchone()
    if verify is None:
        return render_template("classrooms.html", taught=taught, taken=taken, joinMessage="Invalid class ID or join code inputted.")
    
    db.execute("INSERT INTO taken VALUES (?,?)", (id, class_id))
    con.commit()

    return redirect("/classrooms")

@app.route("/assignment/<id>")
@login_required
def assignment(id):

    user = session.get("user_id")
    class_info = db.execute("SELECT topic_id, classroom_id FROM assignments WHERE id = ?", (id,)).fetchone()

    if class_info is None:
        return render_template("error.html", error=[404, "Assignment could not be found"])
    
    class_name = db.execute("SELECT name FROM classrooms WHERE id = ? AND teacher_id = ?", (class_info[1], user)).fetchone()

    if class_name is None:
        return render_template("error.html", error=[403, "You do not have permission to access this page."])
    
    topic = None
    for unit in units:
        if unit['id'] == class_info[0]:
            topic = unit['topic']
            break

    if topic is None:
        return render_template("error.html", error=[501, "Could not fetch assignment topic"])
    
    _students = db.execute("SELECT user_id FROM taken WHERE classroom_id = ?", (class_info[1],)).fetchall()
    students = []

    for student in _students:
        m = get_topic_mastery(student[0], class_info[0])
        info = {
            "name": db.execute("SELECT display FROM users WHERE id = ?", (student[0],)).fetchone()[0],
            "time_spent": int_to_time(m[1], seconds=True),
            "progress": m[0],
        }

        info["accuracy"] = 0
        if m[3] != 0:
            info["accuracy"] = round(m[2] / m[3] * 100, 1)

        students.append(info)
    
    return render_template("assignment.html", assignment={"topic": topic, "class_name": class_name[0]}, students=students)

@app.route("/fetchproblem", methods=["POST"])
def fetch_problem():
    topic = request.json.get("topic")

    for t in units:
        if t["id"] == int(topic):
            topic = deepcopy(t)
            break

    progress = get_topic_mastery(session.get("user_id"), topic["id"])[0]

    problems = [generate_problem(topic) for i in range(3)]
    probabilities = [(progress - p["difficulty"])**2 for p in problems]
    return jsonify({"problem": random.choices(problems, probabilities)})

@app.route("/updateprogress", methods=["POST"])
def updateprogress():
    topic = request.json.get("topic")

    for t in units:
        if t["id"] == int(topic):
            topic = deepcopy(t)
            break
    
    correct = request.json.get("correct")
    difficulty = request.json.get("difficulty")
    time = request.json.get("time")

    mastery = get_topic_mastery(session.get("user_id"), topic["id"])
    if correct:
        new_mastery = mastery[0] + 5 - (mastery[0] / 100 - difficulty) * 4
    else:
        new_mastery = mastery[0] - (5 - (mastery[0] / 100 - difficulty) * 4)
    
    if new_mastery > 100:
        new_mastery = 100
    elif new_mastery < 0:
        new_mastery = 0
    
    new_mastery = round(new_mastery)

    acc = [0,0]
    if session.get("user_id"):
        if db.execute("SELECT * FROM mastery WHERE topic_id = ? AND user_id = ?", (topic["id"], session.get("user_id"))).fetchone() is not None:
            acc = get_topic_mastery(session.get("user_id"), topic["id"])[2:]
            db.execute("UPDATE mastery SET time = ?, progress = ?, correct = ?, total = ? WHERE topic_id = ? AND user_id = ?", (time, new_mastery, acc[0] + int(correct), acc[1] + 1,topic["id"], session.get("user_id")))
        else:
            db.execute("INSERT INTO mastery (time, progress, correct, total, user_id, topic_id) VALUES (?,?,?,?,?,?)",(time, new_mastery, int(correct), 1, session.get("user_id"), topic["id"]))
    
    con.commit()

    return jsonify({"progress": new_mastery, "correct": acc[0], "total": acc[1]})

def get_classrooms(id):
    _taken = db.execute("SELECT id, teacher_id, name FROM classrooms WHERE id IN (SELECT classroom_id FROM taken WHERE user_id = ?)", (id,)).fetchall()
    _taught = db.execute("SELECT id, name FROM classrooms WHERE teacher_id = ?", (id,)).fetchall()

    taken = []
    taught = []

    for cls in _taken:
        taken.append({
            "id": cls[0],
            "name": cls[2],
            "teacher_name": db.execute("SELECT display FROM users WHERE id = ?", (cls[1],)).fetchone()[0],
            "enrolled": db.execute("SELECT COUNT(*) FROM users WHERE id IN (SELECT user_id FROM taken WHERE classroom_id = ?)", (cls[0],)).fetchone()[0]
        })
    for cls in _taught:
        taught.append({
            "id": cls[0],
            "name": cls[1],
            "teacher_name": db.execute("SELECT display FROM users WHERE id = ?", (id,)).fetchone()[0],
            "enrolled": db.execute("SELECT COUNT(*) FROM users WHERE id IN (SELECT user_id FROM taken WHERE classroom_id = ?)", (cls[0],)).fetchone()[0]
        })
    
    return taught, taken

def get_topic_mastery(user_id, topic_id):
    if user_id:
        mastery = db.execute(f"SELECT progress, time, correct, total FROM mastery WHERE topic_id = ? AND user_id = ?", (topic_id, user_id)).fetchone()

        if mastery is None:
            return [0,0,0,0]
        
        else:
            return list(mastery)
        
    else:
        return [0,0,0,0]

def generate_problem(topic):
    problem = deepcopy(random.choice(topic["problems"]))

    problem["preface"] = random.choice(problem["preface"])
    if problem["type"] == "mcq":
        random.shuffle(problem["options"])
    
    variables = {}
    shape = False
    for n, val in problem["variables"].items():
        if val["type"] == "randomshape":
            shape = True
            break

    for name, var in problem["variables"].items():
        if var["type"] == "randomnum":
            if isinstance(var["min"], str):
                var["min"] = int(eval(var["min"], {}, variables))
            if isinstance(var["max"], str):
                var["max"] = int(eval(var["max"], {}, variables))
            
            while True:
                if var["whole"]:
                    variables[name] = random.randint(var["min"], var["max"])
                else:
                    precision = 10 ** var["precision"]
                    variables[name] = random.randint(var["min"] * precision, var["max"] * precision) / precision

                repeats = False
                digits = []
                for digit in str(variables[name]):
                    if digit in digits:
                        repeats = True
                        break
                    digits.append(digit)

                try:
                    if var["repeats"] == True or not repeats:
                        break
                except:
                    break


        elif var["type"] == "randomshape":
            value = random.choice(var["options"])

            variables[name] = f'<img width="32" height="32" src="/static/shapes/{value}.png">'
        elif var["type"] == "digit":
            index = random.randint(0, len(str(variables[var["in"]])) - 1)

            variables[name] = int(str(variables[var["in"]])[index])
    
    problem["preface"] = replace_variables(problem["preface"], variables)
    problem["problem"] = replace_variables(problem["problem"], variables)

    if problem["type"] == "mcq":
        o = []
        for option in problem["options"]:
            opt = replace_variables(option, variables)
            
            if not shape:
                opt = eval(opt)
                if int(opt) == opt:
                    opt = int(opt)
            o.append(opt)
                    
        problem["options"] = o
    
    if shape:
        problem["answer"] = eval(problem["answer"], {}, variables)
    else:
        problem["answer"] = round(eval(problem["answer"], {}, variables), 2)
        if int(problem["answer"]) == problem["answer"]:
            problem["answer"] = int(problem["answer"])
    problem["difficulty"] = int(eval(problem["difficulty"], {}, variables))

    return problem

def replace_variables(template, variables):
    pattern = r'@([^#]+)#'

    def evaluate_expression(match):
        expression = match.group(1)

        try:
            result = eval(expression, {}, variables)
            return str(result)
        except Exception as e:
            return f"Error: {e}"

    result = sub(pattern, evaluate_expression, template)
    
    return result

def int_to_time(integer, seconds=False):
    if seconds:
        minutes = math.floor(integer / 60)
        second = integer % 60
    else:
        minutes = integer % 60

    hours = math.floor(minutes / 60)
    days = hours / 24
    hours = hours % 24

    days = math.floor(days)

    values = [days, hours, minutes]
    
    if seconds:
        values.append(second)

    for c, t in enumerate(values):
        if t != 0:
            labels = ["days", "hours", "minutes"]
            if seconds:
                labels.append("seconds")
            r_value = ""
            for i in range(c, 3):
                if values[i] == 1:
                    r_value = r_value + f"{values[i]} {labels[i][0:-1]} "
                else:
                    r_value = r_value + f"{values[i]} {labels[i]} "
            r_value = r_value.strip()
            return r_value
    
    return "0 minutes"

if __name__ == "__main__":
    app.run(debug=False)