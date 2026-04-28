from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib
from openai import OpenAI
api_key = os.getenv("AIzaSyBJOV6T_l1zhbXwUJHpTE9IpIdRXMA2iJo")
if api_key:
    client = OpenAI(api_key=api_key)
else:
    client = None
#----------model trarining----------
import pandas as pd

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(BASE_DIR, "data", "calories.csv")
    df = pd.read_csv(csv_path)
    print("SUCCESS: DATA LOADED SUCCESSFULLY")
    print(df.head())
except Exception as e:
    print("ERROR:", e)

app = Flask(__name__)
app.secret_key = "secret123"

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        calories REAL
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS tracker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    month TEXT,
    day INTEGER,
    status INTEGER
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS diet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    meal TEXT,
    item TEXT,
    calories INTEGER,
    protein INTEGER,
    carbs INTEGER,
    fats INTEGER
    )''')
#ai chatbot
    c.execute('''
    CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    message TEXT,
    response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
     )''')

    conn.commit()
    conn.close()

init_db()

# ---------- MODEL ----------
MODEL_PATH = "model.pkl"

def train_model():
    try:
        df = pd.read_csv("data/calories.csv")
        X = df[['age','weight','duration','heart_rate']]
        y = df['calories']
        model = LinearRegression()
        model.fit(X, y)
        joblib.dump(model, MODEL_PATH)
        return model
    except:
        return None

if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
else:
    model = train_model()

# ---------- ROUTES ----------

@app.route('/')
def home():
    return redirect(url_for('login'))

# LOGIN
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=?", (email,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user'] = user[1]
            return redirect(url_for('dashboard'))

    return render_template('login.html')

# SIGNUP
@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",
                      (name,email,password))
            conn.commit()
        except:
            pass
        conn.close()

        return redirect(url_for('login'))

    return render_template('signup.html')

# DASHBOARD
@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    prediction = None
    tip = None

    if request.method == 'POST':
        try:
            age = float(request.form['age'])
            weight = float(request.form['weight'])
            duration = float(request.form['duration'])
            heart = float(request.form['heart'])

            gender = request.form['gender']
            height = float(request.form['height'])
            temp = float(request.form['temp'])

            if model:
                prediction = model.predict([[age, weight, duration, heart]])[0]
            else:
                prediction = 200  # fallback

            # SAVE DATA
            conn = sqlite3.connect("database.db")
            c = conn.cursor()
            c.execute(
                "INSERT INTO history (user, calories) VALUES (?,?)",
                (session['user'], prediction)
            )
            conn.commit()
            conn.close()

            # Dynamic Tip based on prediction
            if prediction < 200:
                tip = "Light activity. Great start, maybe try adding 10 more minutes next time!"
            elif prediction < 400:
                tip = "Good job! You burned a solid amount of calories. Keep the consistency!"
            else:
                tip = "Amazing! You burned a lot of calories. Remember to hydrate and replenish with protein!"

        except Exception as e:
            print("ERROR:", e)
            prediction = "Error"
            tip = "Invalid input"

    # FETCH CHART DATA (INSIDE FUNCTION ✅)
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT calories FROM history WHERE user=?", (session['user'],))
    chart_data = [row[0] for row in c.fetchall()]
    conn.close()

    # RETURN MUST BE INSIDE FUNCTION ✅ 
    return render_template(
    'dashboard.html',
    user=session['user'],
    prediction=prediction,
    tip=tip,
    chart_data=chart_data
   )

# NAV PAGES

#--------tracker-------

@app.route('/tracker', methods=['GET','POST'])
def tracker():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Ensure year column exists
    try:
        c.execute("ALTER TABLE tracker ADD COLUMN year INTEGER DEFAULT 2026")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    import calendar
    from datetime import datetime
    
    now = datetime.now()
    selected_year = int(request.args.get('year', request.form.get('year', now.year)))
    selected_month = int(request.args.get('month', request.form.get('month', now.month)))

    months = [
        (1, "January"), (2, "February"), (3, "March"), (4, "April"),
        (5, "May"), (6, "June"), (7, "July"), (8, "August"),
        (9, "September"), (10, "October"), (11, "November"), (12, "December")
    ]
    years = list(range(2020, 2031))
    
    selected_month_name = dict(months).get(selected_month)
    num_days = calendar.monthrange(selected_year, selected_month)[1]

    # SAVE DATA
    if request.method == 'POST':
        c.execute("DELETE FROM tracker WHERE user=? AND month=? AND year=?", (session['user'], selected_month_name, selected_year))

        for day in range(1, num_days + 1):
            key = f"{selected_month_name}_{day}"
            status = 1 if key in request.form else 0

            c.execute(
                "INSERT INTO tracker (user, month, day, status, year) VALUES (?,?,?,?,?)",
                (session['user'], selected_month_name, day, status, selected_year)
            )

        conn.commit()
        return redirect(url_for('tracker', year=selected_year, month=selected_month))

    # LOAD DATA
    c.execute("SELECT month, day, status, year FROM tracker WHERE user=?", (session['user'],))
    data = c.fetchall()

    tracker_data = {(m, d, y): s for (m, d, s, y) in data}
    
    view_data = {d: tracker_data.get((selected_month_name, d, selected_year), 0) for d in range(1, num_days + 1)}

    # -------- STREAK LOGIC --------
    checked_days = []

    for (m, d, y), s in tracker_data.items():
        if s == 1:
            try:
                date_obj = datetime.strptime(f"{d} {m} {y}", "%d %B %Y")
                checked_days.append(date_obj)
            except:
                pass

    checked_days.sort()

    current_streak = 0
    longest_streak = 0
    temp_streak = 1

    for i in range(1, len(checked_days)):
        diff = (checked_days[i] - checked_days[i-1]).days

        if diff == 1:
            temp_streak += 1
        elif diff > 1:
            longest_streak = max(longest_streak, temp_streak)
            temp_streak = 1

    longest_streak = max(longest_streak, temp_streak)

    if checked_days:
        today = datetime.now().date()
        last_checked = checked_days[-1].date()
        if (today - last_checked).days <= 1:
            current_streak = temp_streak
        else:
            current_streak = 0

    conn.close() 

    return render_template(
        'tracker.html',
        selected_year=selected_year,
        selected_month=selected_month,
        selected_month_name=selected_month_name,
        num_days=num_days,
        years=years,
        months=months,
        view_data=view_data,
        current_streak=current_streak,
        longest_streak=longest_streak
    )

@app.route('/workout')
def workout():
    return render_template('workout.html')

#<!-- DIET -->
@app.route('/diet', methods=['GET', 'POST'])
def diet():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    diet_type = request.form.get("diet_type", "veg")

    # -------- SAVE DATA --------
    if request.method == 'POST':
     c.execute("DELETE FROM diet WHERE user=?", (session['user'],))

    # ✅ ADD HERE
    meal = request.form.get("meal_title", "Meal")
    item = request.form.get("item", "")

    calories = int(request.form.get("calories") or 0)
    protein = int(request.form.get("protein") or 0)
    carbs = int(request.form.get("carbs") or 0)
    fats = int(request.form.get("fats") or 0)

    c.execute(
        "INSERT INTO diet (user, meal, item, calories, protein, carbs, fats) VALUES (?,?,?,?,?,?,?)",
        (session['user'], meal, item, calories, protein, carbs, fats)
    )

    conn.commit()

    # -------- FETCH DATA --------
    c.execute("SELECT meal, item, calories, protein, carbs, fats FROM diet WHERE user=?", (session['user'],))
    data = c.fetchall()

    total_calories = sum(row[2] for row in data)
    total_protein = sum(row[3] for row in data)
    total_carbs = sum(row[4] for row in data)
    total_fats = sum(row[5] for row in data)

    conn.close()

    return render_template(
        "diet.html",
        data=data,
        total_calories=total_calories,
        protein=total_protein,
        carbs=total_carbs,
        fats=total_fats
    )


# AI CHATBOT

@app.route('/ai')
def ai():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT message, response FROM chat_history WHERE user=? ORDER BY id DESC LIMIT 10", (session['user'],))
    chats = c.fetchall()
    conn.close()

    messages = []
    for msg, res in chats:
        messages.append({"sender": "user", "text": msg})
        messages.append({"sender": "ai", "text": res})

    return render_template("ai.html", messages=messages)

# AI CHATBOT
@app.route('/chat', methods=['POST'])
def chat():
    if 'user' not in session:
        return {"reply": "Login required"}

    data = request.get_json()
    user_msg = data.get("message")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT SUM(calories) FROM history WHERE user=?", (session['user'],))
    burned = c.fetchone()[0] or 0

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role":"user",
                "content": f"User burned {burned} calories. Question: {user_msg}"
            }]
        )
        reply = response.choices[0].message.content
    except:
        reply = "AI not available"

    conn.close()

    # AFTER getting reply
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute(
    "INSERT INTO chat_history (user, message, response) VALUES (?,?,?)",
    (session['user'], user_msg, reply))

    conn.commit()
    conn.close()

    return {"reply": reply}

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

#save tracker
@app.route('/save_tracker', methods=['POST'])
def save_tracker():
    data = request.json['data']

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    for i, val in enumerate(data):
        c.execute("INSERT INTO weekly_tracker (user, day, status) VALUES (?,?,?)",
                  (session['user'], str(i), val))

    conn.commit()
    conn.close()

    return {"msg":"saved"}

# ADMIN ROUTES
@app.route('/admin')
def admin():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Stats
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM history")
    total_calorie_records = c.fetchone()[0]
    
    c.execute("SELECT SUM(calories) FROM history")
    total_calories_burned = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM diet")
    total_diet_entries = c.fetchone()[0]
    
    stats = {
        "total_users": total_users,
        "total_calorie_records": total_calorie_records,
        "total_calories_burned": total_calories_burned,
        "total_diet_entries": total_diet_entries
    }
    
    # Users
    c.execute("SELECT id, name, email FROM users")
    users = [dict(row) for row in c.fetchall()]
    
    # Diet Records (Recent 10)
    c.execute("SELECT user, meal, item, calories FROM diet ORDER BY id DESC LIMIT 10")
    diet_records = [dict(row) for row in c.fetchall()]
    
    # Chat History (Recent 10)
    try:
        c.execute("SELECT user, message, response, created_at FROM chat_history ORDER BY id DESC LIMIT 10")
        chat_history = [dict(row) for row in c.fetchall()]
    except Exception:
        chat_history = []
    
    # Chart 1: Calories Trend (Last 10 platform-wide)
    c.execute("SELECT id, calories FROM history ORDER BY id DESC LIMIT 10")
    recent_history = c.fetchall()
    import json
    chart_labels = json.dumps([f"Record {row['id']}" for row in reversed(recent_history)])
    chart_data_calories = json.dumps([row['calories'] for row in reversed(recent_history)])
    
    # Chart 2: User Activity (Top 5 users with most history entries)
    c.execute("SELECT user, COUNT(*) as count FROM history GROUP BY user ORDER BY count DESC LIMIT 5")
    top_users = c.fetchall()
    chart_user_names = json.dumps([row['user'] for row in top_users])
    chart_user_activity = json.dumps([row['count'] for row in top_users])
    
    conn.close()
    
    return render_template('admin.html', 
                           stats=stats, 
                           users=users, 
                           diet_records=diet_records, 
                           chat_history=chat_history,
                           chart_labels=chart_labels,
                           chart_data_calories=chart_data_calories,
                           chart_user_names=chart_user_names,
                           chart_user_activity=chart_user_activity)

@app.route('/delete_user/<int:id>')
def delete_user(id):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/export_users')
def export_users():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT id, name, email FROM users")
    users = c.fetchall()
    conn.close()
    
    import io
    import csv
    from flask import Response
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Email'])
    for user in users:
        writer.writerow(user)
        
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=users.csv"})

# RUN
if __name__ == '__main__':
    app.run(debug=True)
