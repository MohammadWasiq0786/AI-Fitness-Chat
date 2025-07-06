# app.py
from flask import Flask, render_template, request, jsonify
import sqlite3
import os
import uuid
from euriai import EuriaiClient
from dotenv import load_dotenv

# Load model
EURI_API_KEY = os.getenv("EURI_API_KEY")
client = EuriaiClient(api_key=EURI_API_KEY, model="gpt-4.1-nano")

DATABASE= "database/database.db"

app = Flask(__name__)

# Initialize DB
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dietary_preferences TEXT,
        fitness_goals TEXT,
        lifestyle_factors TEXT,
        dietary_restrictions TEXT,
        health_conditions TEXT,
        user_query TEXT,
        diet_types TEXT,
        workouts TEXT,
        breakfasts TEXT,
        dinners TEXT,
        additional_tips TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        user_query TEXT,
        ai_response TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS download_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        export_type TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()

init_db()

# AI Generator
def generate_recommendation(dietary_preferences, fitness_goals, lifestyle_factors,
                            dietary_restrictions, health_conditions, user_query):
    prompt = f"""
    dietary preferences: {dietary_preferences}
    fitness goals: {fitness_goals}
    lifestyle factors: {lifestyle_factors}
    dietary restrictions: {dietary_restrictions}
    health conditions: {health_conditions}
    user query: {user_query}

    Provide:
    Diet Recommendations: list
    Workout Options: list
    Meal Suggestions (breakfast): list
    Dinner Options: list
    Additional Recommendations: list
    """
    
    response = client.generate_completion(prompt=prompt, temperature=0.5, max_tokens=1000)
    ai_text = response['choices'][0]['message']['content'] if 'choices' in response else ""

    return ai_text.strip()
    # response = model.generate_content(prompt)
    # return response.text if response else ""

@app.route('/')
def index():
    return render_template("index.html", recommendations=None)

@app.route('/recommendations', methods=['POST'])
def recommendations():
    form = request.form
    session_id = str(uuid.uuid4())

    text_response = generate_recommendation(
        form['dietary_preferences'],
        form['fitness_goals'],
        form['lifestyle_factors'],
        form['dietary_restrictions'],
        form['health_conditions'],
        form['user_query']
    )

    rec = {
        "diet_types": [],
        "workouts": [],
        "breakfasts": [],
        "dinners": [],
        "additional_tips": []
    }

    section = None
    for line in text_response.splitlines():
        if "Diet Recommendations" in line:
            section = "diet_types"
        elif "Workout Options" in line:
            section = "workouts"
        elif "Meal Suggestions" in line:
            section = "breakfasts"
        elif "Dinner Options" in line:
            section = "dinners"
        elif "Additional Recommendations" in line:
            section = "additional_tips"
        elif line.strip() and section:
            rec[section].append(line.strip())

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""INSERT INTO chat_history (session_id, user_query, ai_response)
                 VALUES (?, ?, ?)""", (session_id, form['user_query'], text_response))

    c.execute("""INSERT INTO recommendations (
        dietary_preferences, fitness_goals, lifestyle_factors, dietary_restrictions,
        health_conditions, user_query, diet_types, workouts, breakfasts, dinners, additional_tips)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
        form['dietary_preferences'], form['fitness_goals'], form['lifestyle_factors'],
        form['dietary_restrictions'], form['health_conditions'], form['user_query'],
        "\n".join(rec['diet_types']), "\n".join(rec['workouts']), "\n".join(rec['breakfasts']),
        "\n".join(rec['dinners']), "\n".join(rec['additional_tips'])
    ))
    conn.commit()
    conn.close()

    return render_template("index.html", recommendations=rec, session_id=session_id)

@app.route('/log-download', methods=['POST'])
def log_download():
    data = request.get_json()
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO download_logs (session_id, export_type) VALUES (?, ?)",
              (data['session_id'], data['export_type']))
    conn.commit()
    conn.close()
    return jsonify({"status": "logged"})

if __name__ == '__main__':
    app.run(debug=True)