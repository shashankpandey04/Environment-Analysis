from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "your_secret_key"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="che"
)
def is_admin(username):
    cursor = db.cursor()
    query = "SELECT admin FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    result = cursor.fetchone()
    cursor.close()
    if result and result[0] == 1:
        return True
    else:
        return False

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = db.cursor()
        query = "SELECT * FROM users WHERE username = %s AND password = %s"
        cursor.execute(query, (username, password))
        user = cursor.fetchone()
        cursor.close()
        if user:
            session['username'] = username
            if is_admin(username):
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('data_display'))
        else:
            return "Invalid username or password"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('landing'))

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        username = session['username']
        return render_template('dashboard.html', username=username, admin=is_admin(username))
    else:
        return redirect(url_for('login'))
    
@app.route('/profile')
def profile():
    if 'username' in session:
        username = session['username']
        return render_template('landing.html', username=username, admin=is_admin(username))
    else:
        return redirect(url_for('login'))

@app.route('/data_entry')
def data_entry():
    if 'username' in session and is_admin(session['username']):
        return render_template('data_entry.html')
    else:
        return redirect(url_for('dashboard'))

@app.route('/data_entry_submit', methods=['POST'])
def data_entry_submit():
    if 'username' in session and is_admin(session['username']):
        location = request.form['location']
        compliance_type = request.form['compliance_type']
        compliance_details = request.form['compliance_details']
        table_name = f"{compliance_type.lower().replace(' ', '_')}_assessments"
        cursor = db.cursor()
        query = f"INSERT INTO {table_name} (site_location, compliance_type, compliance_details) VALUES (%s, %s, %s)"
        cursor.execute(query, (location, compliance_type, compliance_details))
        db.commit()
        cursor.close()
        return redirect(url_for('data_entry'))
    else:
        return "You are not authorized to access this page."

@app.route('/data_display', methods=['GET', 'POST'])
def data_display():
    category = None
    location = None
    locations = []
    assessments = []

    if request.method == 'POST':
        category = request.form['category']
        location = request.form['location']
        cursor = db.cursor()
        query = "SELECT DISTINCT site_location FROM {}_assessments".format(category.lower().replace(" ", "_"))
        cursor.execute(query)
        locations = [loc[0] for loc in cursor.fetchall()]
        cursor.close()
        cursor = db.cursor(dictionary=True)
        query = "SELECT * FROM {}_assessments WHERE site_location = %s".format(category.lower().replace(" ", "_"))
        cursor.execute(query, (location,))
        assessments = cursor.fetchall()
        cursor.close()

    return render_template('data_display.html', category=category, location=location, locations=locations, assessments=assessments)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)
