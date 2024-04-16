from flask import Flask, render_template, request, redirect, url_for, session,flash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import mysql.connector

app = Flask(__name__)
app.secret_key = "your_secret_key"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="che"
)
cursor = db.cursor()

def is_admin(username):
    query = "SELECT admin FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    result = cursor.fetchone()
    if result and result[0] == 1:
        return True
    else:
        return False

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/report')
def report():
    return render_template('report.html')

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
            flash("Invalid credentials. Please try again.", "error")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('landing'))

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        username = session['username']
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM issues")
        total_reported_issues = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM issues WHERE status = 'false'")
        total_unsolved_issues = cursor.fetchone()[0]
        return render_template('dashboard.html', username=username, admin=is_admin(username), total_reported_issues=total_reported_issues, total_unsolved_issues=total_unsolved_issues)
    else:
        return render_template("unauth.html")

@app.route('/issues')
def issues():
    if 'username' in session:
        cursor.execute("SELECT * FROM issues WHERE status = 'false'")
        active_issues = cursor.fetchall()
        print(active_issues)  # Check to see the data in console
        return render_template('issues.html', issues=active_issues)
    else:
        return render_template("unauth.html")

@app.route('/resolve_issue/<int:ticket_id>', methods=['POST'])
def resolve_issue(ticket_id):
    if 'username' in session:
        cursor.execute("DELETE FROM issues WHERE ticket_id = %s", (ticket_id,))
        db.commit()
        return redirect('/issues')
    else:
        return render_template("unauth.html")
    
@app.route('/data_entry')
def data_entry():
    if 'username' in session and is_admin(session['username']):
        return render_template('data_entry.html')
    else:
        return render_template("unauth.html")

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


def send_mailtrap_email(receiver_email, ticket_id, location, issue_type, description, contact):
    sender_email = "mailtrap@demomailtrap.com"
    smtp_server = "live.smtp.mailtrap.io"
    smtp_port = 587
    smtp_username = "api"
    smtp_password = "e12aae311c338770c720474e01f9d387"
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "Issue Report Confirmation"
    body = f"""\
    Your issue has been successfully reported.\n\n
    Ticket ID: {ticket_id}\n
    Location: {location}\n
    Issue Type: {issue_type}\n
    Description: {description}\n
    Contact: {contact}
    """
    message.attach(MIMEText(body, "plain"))
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(sender_email, receiver_email, message.as_string())

@app.route("/submit-issue", methods=['POST'])
def report_issue():
    if request.method == 'POST':
        location = request.form['location']
        issue_type = request.form['issue_type']
        description = request.form['description']
        contact = request.form['contact']
        email = request.form['email']
        try:
            cursor.execute("INSERT INTO issues (location, issue_type, description, contact, email,status) VALUES (%s, %s, %s, %s, %s , %s)", (location, issue_type, description, contact, email,'false'))
            db.commit()
            ticket_id = cursor.lastrowid
            send_mailtrap_email(email, ticket_id, location, issue_type, description, contact)
            return render_template('ticket_created.html', ticket_id=ticket_id, mail_id=email)
        except Exception as e:
            db.rollback()
            return "Error: " + str(e)
        
@app.route("/ticket_created/<ticket_id>")
def ticket_created(ticket_id,mail_id):
    return render_template('ticket_created.html', ticket_id=ticket_id,mail_id=mail_id)

@app.route("/satellite-images")
def satellite_images():
    return render_template('satellite_images.html')

@app.route('/vegitation')
def vegitation():
    return render_template('vegitation.html')

@app.route("/temp")
def temp():
    return render_template('temp.html')

@app.route("/rain")
def rain():
    return render_template('rain.html')

@app.route('/soil')
def soil():
    return render_template('soil.html')

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)
