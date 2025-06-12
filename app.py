from flask import Flask, render_template, request, jsonify, session, redirect,url_for, send_from_directory
import requests
import mysql.connector
import random
import string
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


app = Flask(__name__)
app.secret_key = 'migrantcare'
app.config['SESSION_COOKIE_NAME'] = 'migrantcare'  # You can specify the session cookie name
otp_storage = {}


# MySQL DB Connection (Correct configuration)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'job'
}

def init_db():
    try:
        conn = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
        )
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS job")
        conn.commit()
        conn.close()

        # Now connect to the new DB
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Your existing table creation code here...
        cursor.execute("""CREATE TABLE IF NOT EXISTS users (...)""")
        # ... (rest of your table creation logic)

        conn.commit()
        conn.close()
        print("Database initialized successfully.")
    except mysql.connector.Error as err:
        print("Error initializing database:", err)


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE,
            email VARCHAR(100) UNIQUE,
            password VARCHAR(500),
            reset_token VARCHAR(100)  -- Token to verify password reset
        )
    """)
    cursor.execute("""
    CREATE TABLE if not exists contact_queries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    subject VARCHAR(255),
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) """)

    cursor.execute("""
    CREATE TABLE if not exists requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    user_id INT NOT NULL,
    status ENUM('accepted', 'rejected') DEFAULT 'rejected',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) """)
    
    cursor.execute(""" CREATE TABLE if not exists messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_type ENUM('user', 'admin') NOT NULL,
    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,
    content TEXT NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP

) """)


    cursor.execute("""
    CREATE TABLE if not exists admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(100),
    password VARCHAR(255) NOT NULL
) """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        admin_id INT,
        title VARCHAR(255) NOT NULL,
        description TEXT NOT NULL,
        responsibilities TEXT,
        qualifications TEXT,
        company_name TEXT,
        category VARCHAR(100) NOT NULL,
        location VARCHAR(255) NOT NULL,
        job_type VARCHAR(100) NOT NULL,
        job_nature VARCHAR(100),
        salary INT NOT NULL,
        vacancy INT,
        published_on DATE,
        deadline DATE NOT NULL,
        company_description TEXT,
        image VARCHAR(255) NOT NULL,
        longitude FLOAT,
        latitude FLOAT
    )
""")
    cursor.execute("""
    CREATE TABLE if not exists bookmark (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    job_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, job_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
) """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_applications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        job_id INT NOT NULL,
        name VARCHAR(100),
                   user_id INT NOT NULL,
        email VARCHAR(100),
        portfolio VARCHAR(255),
        cover_letter TEXT,
        resume_filename VARCHAR(255),
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status ENUM('Pending', 'Accepted', 'Rejected') DEFAULT 'Pending'
    )
""")


    
    cursor.execute(""" CREATE TABLE IF NOT EXISTS job_reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    user_name VARCHAR(100) NOT NULL,
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
) """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(15),
    location VARCHAR(100),
    experience INT,
    last_job VARCHAR(100),
    skills VARCHAR(255),
    qualification VARCHAR(100),
    institution VARCHAR(100),
    passing_year INT,
    preferred_role VARCHAR(100),
    preferred_location VARCHAR(100),
    expected_salary DECIMAL(10, 2),
    dob DATE,
    gender VARCHAR(10),
    aadhaar_number VARCHAR(100), aadhaar_image VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES users(id)
)
                    """)
    conn.commit()
    conn.close()

def get_coordinates(location):
    """Fetch latitude and longitude from location string using OpenStreetMap"""
    try:
        response = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': location, 'format': 'json'},
            headers={'User-Agent': 'job-portal-app'}  # Required by Nominatim
        )
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
        else:
            return None, None
    except Exception as e:
        print("Geocoding error:", e)
        return None, None

def send_otp_email(email, otp):
    sender_email = "careskill360@gmail.com"
    sender_password ="rurfaqlshhkrrwxg"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your OTP Verification Code"
    msg["From"] = sender_email
    msg["To"] = email

    text = f"Your OTP code is: {otp}"
    msg.attach(MIMEText(text, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, email, msg.as_string())
# Helper function to send email
def send_reset_email(to_email, token):
    from_email = 'careskill360@gmail.com'  # Replace with your email address
    password = 'rurfaqlshhkrrwxg'  # Replace with your email password or app-specific password
    subject = 'Password Reset Request'
    body = f'Click the link to reset your password: http://localhost:5000/reset-password/{token}'

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        print("Email sent successfully.")
    except Exception as e:
        print("Failed to send email:", e)

# Generate a random token for password reset link
def generate_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=20))

from werkzeug.security import generate_password_hash

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data['username']
    email = data['email']
    password = data['password']

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        if cursor.fetchone():
            return jsonify({'message': 'Username or email already exists'}), 400

        otp = str(random.randint(100000, 999999))
        otp_storage[email] = {'otp': otp, 'data': {'username': username, 'email': email, 'password': password}}

        send_otp_email(email, otp)

        return jsonify({'message': 'OTP sent to email'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data['email']
    otp = data['otp']

    if email not in otp_storage:
        return jsonify({'message': 'OTP not found or expired'}), 400

    if otp_storage[email]['otp'] != otp:
        return jsonify({'message': 'Invalid OTP'}), 400

    try:
        user_data = otp_storage[email]['data']
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        hashed_password = generate_password_hash(user_data['password'])
        cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                       (user_data['username'], user_data['email'], hashed_password))
        conn.commit()

        del otp_storage[email]

        return jsonify({'message': 'Registration successful'}), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        conn.close()

UPLOAD_FOLDER = 'uploads'  # assuming it's at the root level
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/api/apply', methods=['POST'])
def apply_job():
    try:
        name = request.form['name']
        email = request.form['email']
        portfolio = request.form['portfolio']
        cover_letter = request.form['cover_letter']
        job_id = request.form['job_id']
        user_id = session["user_id"]

        resume = request.files.get('resume')
        filename = None

        if resume:
            filename = secure_filename(resume.filename)
            resume.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Check if the user has already applied for the same job using SELECT COUNT
        cursor.execute("SELECT COUNT(*) FROM job_applications WHERE user_id = %s AND job_id = %s", (user_id, job_id))
        existing_application_count = cursor.fetchone()[0]  # Get the count result

        if existing_application_count > 0:
            # If the count is greater than 0, it means the application already exists
            return jsonify({'success': False, 'message': 'You have already applied for this job.'}), 409

        # Insert the new application if no existing application found
        query = '''
            INSERT INTO job_applications (job_id, user_id, name, email, portfolio, cover_letter, resume_filename, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        '''
        cursor.execute(query, (job_id, user_id, name, email, portfolio, cover_letter, filename, 'Pending'))
        conn.commit()

        return jsonify({'success': True, 'message': 'Application submitted successfully!'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        cursor.close()  # Close the cursor
        conn.close()  # Close the database connection


@app.route('/api/update-application-status/<int:application_id>', methods=['PUT'])
def update_application_status(application_id):
    data = request.get_json()
    new_status = data.get('status')

    if new_status not in ['Pending', 'Accepted', 'Rejected']:
        return jsonify({'message': 'Invalid status'}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("UPDATE job_applications SET status = %s WHERE id = %s", (new_status, application_id))
        conn.commit()
        return jsonify({'message': f'Status updated to {new_status}.'})
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        conn.close()


# Create a route to serve images from the uploads folder
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
@app.route('/api/joblisting', methods=['GET'])
def job_listings():
    job_type = request.args.get('job_type', default='all')  # Get the job type parameter, default to 'all'

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Query based on job_type
        if job_type == 'all':
            cursor.execute("SELECT * FROM jobs")
        else:
            cursor.execute("SELECT * FROM jobs WHERE job_type = %s", (job_type,))

        jobs = cursor.fetchall()

        return jsonify(jobs)  # Return the jobs in JSON format

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    # Check if user is logged in by checking session
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    user_id = session['user_id']  # Get user ID from session

    if request.method == 'POST':
        # Get the form data from the request
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        location = request.form.get('location')
        experience = request.form.get('experience')
        last_job = request.form.get('last_job')
        skills = request.form.get('skills')
        qualification = request.form.get('qualification')
        institution = request.form.get('institution')
        passing_year = request.form.get('passing_year')
        preferred_role = request.form.get('preferred_role')
        preferred_location = request.form.get('preferred_location')
        expected_salary = request.form.get('expected_salary')
        dob = request.form.get('dob')
        gender = request.form.get('gender')
        
        # Get the Aadhaar card number and image
        aadhaar_number = request.form.get('aadhaar_number')
        aadhaar_image = request.files.get('aadhaar_image')

        # Save the Aadhaar image to the server
        aadhaar_image_filename = None
        if aadhaar_image:
            aadhaar_image_filename = os.path.join('uploads', aadhaar_image.filename)
            aadhaar_image.save(aadhaar_image_filename)

        # Insert the form data into the database, associating it with the logged-in user
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            # Insert data into the profile table, assuming there is a profile table
            cursor.execute("""
                INSERT INTO profiles (
                    user_id, first_name, last_name, email, phone, location,
                    experience, last_job, skills, qualification, institution,
                    passing_year, preferred_role, preferred_location,
                    expected_salary, dob, gender, aadhaar_number, aadhaar_image
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s)
            """, (
                user_id, first_name, last_name, email, phone, location,
                experience, last_job, skills, qualification, institution,
                passing_year, preferred_role, preferred_location,
                expected_salary, dob, gender, aadhaar_number, aadhaar_image_filename
            ))

            conn.commit()
            return redirect(url_for('profile'))  # Redirect to the profile page after saving data

        except Exception as e:
            return jsonify({'message': str(e)}), 500
        finally:
            conn.close()

    return render_template('index.html')
@app.route('/send_request_chat', methods=['POST'])
def send_request_chat():
    # Get admin ID from session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized: Admin not logged in'}), 401

    # Get user ID from form
    admin_id = request.form.get('admin_id')
    if not admin_id:
        return jsonify({'error': 'User ID is required'}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(buffered=True)  # Use a buffered cursor

        # Check if a request already exists for this user
        cursor.execute("""
            SELECT id FROM requests
            WHERE admin_id = %s AND user_id = %s
        """, (admin_id, user_id))
        existing_request = cursor.fetchone()

        if existing_request:
            # If a request exists, return a success message (status 201)
            return jsonify({'message': 'Request already exists and accepted by chatbot'}), 201

        # Insert into requests table with status = 'accepted' (chatbot default)
        cursor.execute("""
            INSERT INTO requests (admin_id, user_id, status)
            VALUES (%s, %s, 'accepted')
        """, (admin_id, user_id))
        conn.commit()

        return jsonify({'message': 'Request sent and accepted by chatbot'}), 201

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/send_request', methods=['POST'])
def send_request():
    # Get admin ID from session
    admin_id = session.get('admin_id')
    if not admin_id:
        return jsonify({'error': 'Unauthorized: Admin not logged in'}), 401

    # Get user ID from form
    user_id = request.form.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(buffered=True)  # Use a buffered cursor

        # Check if a request already exists for this user
        cursor.execute("""
            SELECT id FROM requests
            WHERE admin_id = %s AND user_id = %s
        """, (admin_id, user_id))
        existing_request = cursor.fetchone()

        if existing_request:
            # If a request exists, return a success message (status 201)
            return jsonify({'message': 'Request already exists and accepted by chatbot'}), 201

        # Insert into requests table with status = 'accepted' (chatbot default)
        cursor.execute("""
            INSERT INTO requests (admin_id, user_id, status)
            VALUES (%s, %s, 'accepted')
        """, (admin_id, user_id))
        conn.commit()

        return jsonify({'message': 'Request sent and accepted by chatbot'}), 201

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/api/bookmarked-jobs', methods=['GET'])
def get_bookmarked_jobs():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized: User not logged in'}), 401

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch job IDs from the bookmark table
        cursor.execute("""
            SELECT job_id FROM bookmark WHERE user_id = %s
        """, (user_id,))
        job_ids = [row['job_id'] for row in cursor.fetchall()]

        if not job_ids:
            return jsonify([])

        # Fetch job details for the bookmarked jobs
        cursor.execute("""
            SELECT * FROM jobs WHERE id IN (%s)
        """ % ','.join(['%s'] * len(job_ids)), tuple(job_ids))
        jobs = cursor.fetchall()

        return jsonify(jobs)

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/bookmark', methods=['POST'])
def bookmark_job():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    data = request.get_json()
    job_id = data.get('job_id')
    user_id = session['user_id']

    if not job_id:
        return jsonify({'success': False, 'message': 'Job ID is required'}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Check if the job is already bookmarked
        cursor.execute("SELECT * FROM bookmark WHERE user_id = %s AND job_id = %s", (user_id, job_id))
        existing = cursor.fetchone()

        if existing:
            return jsonify({'success': False, 'message': 'Job already bookmarked'}), 409

        # Insert new bookmark
        cursor.execute("INSERT INTO bookmark (user_id, job_id) VALUES (%s, %s)", (user_id, job_id))
        conn.commit()

        return jsonify({'success': True, 'message': 'Job bookmarked successfully'}), 200

    except mysql.connector.Error as e:
        return jsonify({'success': False, 'message': str(e)}), 500

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

    finally:
        conn.close()


from werkzeug.security import check_password_hash

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Get user with username
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user[3], password):  # assuming password is in 4th column
            session['user_id'] = user[0]
            session['username'] = user[1]

            # Check if user already has a profile
            cursor.execute("SELECT * FROM profiles WHERE user_id = %s", (user[0],))
            profile = cursor.fetchone()

            if profile:
                redirect_url = '/'
            else:
                redirect_url = '/form'

            return jsonify({'message': f'Welcome back, {username}!', 'redirect': redirect_url}), 200
        else:
            return jsonify({'message': 'Invalid username or password'}), 401
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        conn.close()



# Forgot Password API
@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data['email']

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Check if email exists in the database
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            # Generate reset token
            token = generate_token()
            cursor.execute("UPDATE users SET reset_token = %s WHERE email = %s", (token, email))
            conn.commit()

            # Send reset email with the generated token
            send_reset_email(email, token)

            return jsonify({'message': 'Password reset link has been sent to your email.'})
        else:
            return jsonify({'message': 'No user found with that email.'}), 400
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        conn.close()


import csv
import os
@app.route('/api/post-job', methods=['POST'])
def post_job():
    conn = None
    try:
        admin_id = session.get('admin_id')
        print("Session data: ", session)  # Prints the entire session dictionary
        print(f"Admin ID: {admin_id}")  # Prints the admin_id value specifically

        if not admin_id:
            return jsonify({'message': 'Admin not logged in!'}), 401

        # ✅ Collect form data
        title = request.form['title']
        description = request.form['description']
        responsibilities = request.form['responsibilities']
        qualifications = request.form['qualifications']
        category = request.form['category']
        location = request.form['location']
        job_type = request.form['job_type']
        job_nature = request.form['job_nature']
        salary = request.form['salary']
        company_name = request.form['company_name']
        vacancy = request.form['vacancy']
        published_on = request.form['published_on']
        deadline = request.form['deadline']
        company_description = request.form['company_description']
        image = request.files['image']
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        # ✅ Save uploaded image
        image_filename = os.path.join('uploads', image.filename)
        image.save(image_filename)

        # ✅ Save to database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO jobs (
                title, description, responsibilities, qualifications,
                category, location, job_type, job_nature, salary,
                vacancy, published_on, deadline, company_description,
                image, admin_id, latitude, longitude
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            title, description, responsibilities, qualifications,
            category, location, job_type, job_nature, salary,
            vacancy, published_on, deadline, company_description,
            image_filename, admin_id, latitude, longitude
        ))

        conn.commit()

        # ✅ Save to CSV file (3 times)
        csv_file = 'job_posts.csv'
        file_exists = os.path.isfile(csv_file)

        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    'title', 'description', 'responsibilities', 'qualifications',
                    'category', 'location', 'job_type', 'job_nature', 'salary',
                    'company_name', 'vacancy', 'published_on', 'deadline',
                    'company_description', 'image', 'admin_id', 'latitude', 'longitude'
                ])
            
            # Row data
            row_data = [
                title, description, responsibilities, qualifications,
                category, location, job_type, job_nature, salary,
                company_name, vacancy, published_on, deadline,
                company_description, image_filename, admin_id, latitude, longitude
            ]

            # Write the same row 3 times
            for _ in range(3):
                writer.writerow(row_data)

        return jsonify({'message': 'Job posted successfully!'}), 200

    except Exception as e:
        return jsonify({'message': f'Error posting job: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()



import math
def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points
    on the Earth using the Haversine formula.
    """
    R = 6371  # Earth radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

@app.route('/api/jobs/nearby', methods=['GET'])
def get_nearby_jobs():
    conn = None
    try:
        # Get latitude and longitude from request
        latitude = request.args.get('latitude')
        longitude = request.args.get('longitude')

        if latitude is None or longitude is None:
            return jsonify({'message': 'Latitude and Longitude are required'}), 400

        latitude = float(latitude)
        longitude = float(longitude)

        radius = 50  # km

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM jobs")
        jobs = cursor.fetchall()

        nearby_jobs = []

        for job in jobs:
            try:
                job_id = job[0]
                job_title = job[2]
                job_location = job[7]
                job_type = job[8]
                job_salary = job[10]
                job_deadline = job[13]
                job_image = job[15]
                job_longitude = float(job[16])
                job_latitude = float(job[17])

                # Debug log (optional)
                print(f"[DEBUG] Job {job_id} coordinates: ({job_latitude}, {job_longitude})")

                # Calculate distance
                distance = calculate_distance(latitude, longitude, job_latitude, job_longitude)

                print(f"[DEBUG] Distance to Job {job_id}: {distance:.2f} km")

                if distance <= radius:
                    nearby_jobs.append({
                        "id": job_id,
                        "title": job_title,
                        "location": job_location,
                        "job_type": job_type,
                        "salary": job_salary,
                        "image": job_image.replace("\\", "/"),  # for consistent web paths
                        "deadline": str(job_deadline)
                    })

            except Exception as job_err:
                print(f"[WARN] Skipping job due to error: {job_err}")
                continue

        return jsonify(nearby_jobs), 200

    except Exception as e:
        return jsonify({'message': f'Error fetching nearby jobs: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()


@app.route('/reset-password/<token>')
def serve_reset_page(token):
    return render_template('reset.html', token=token)  # If using Jinja2 templates

@app.route('/api/reset-password', methods=['POST'])
def reset_pass_link():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('password')  # ✅ Using the correct key

    if not token or not new_password:
        return jsonify({'message': 'Token and password are required.'}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE reset_token = %s", (token,))
        user = cursor.fetchone()

        if not user:
            return jsonify({'message': 'Invalid or expired token'}), 400

        hashed_password = generate_password_hash(new_password)
        cursor.execute("UPDATE users SET password = %s, reset_token = NULL WHERE reset_token = %s",
                       (hashed_password, token))
        conn.commit()

        return jsonify({'message': 'Password has been reset successfully'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500
    finally:
        conn.close()



# Route Definitions
@app.route('/login')
def index():
    return render_template('login.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/reset-password')
def resetpassword():
    return render_template('reset.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/jobnearme')
def jobnearme():
    return render_template('nearbyjobs.html') 
@app.route('/testimonial')
def testimonial():
    return render_template('testimonial.html')

@app.route('/job-list')
def joblist():
    return render_template('job-list.html')
@app.route('/accepted-offer')
def acceptedoffer():
    return render_template('acceptedjob.html')
@app.route('/job-recommendation')
def recommendation():
    return render_template('recommendation.html')

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def recommend_jobs(user_input):
    # Load job data
    df = pd.read_csv('job_posts.csv').drop_duplicates()

    # Fill missing fields with empty strings for compatibility
    df['title'] = df['title'].fillna('')
    df['description'] = df['description'].fillna('')
    df['responsibilities'] = df['responsibilities'].fillna('')
    df['qualifications'] = df['qualifications'].fillna('')

    # Combine text fields for matching
    df['combined'] = df['title'] + ' ' + df['description'] + ' ' + df['responsibilities'] + ' ' + df['qualifications']

    # Vectorize text
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(df['combined'])

    # Transform user input
    user_vec = vectorizer.transform([user_input])

    # Compute similarity
    similarities = cosine_similarity(user_vec, tfidf_matrix).flatten()

    # Get top 5 jobs
    top_indices = similarities.argsort()[-5:][::-1]
    recommendations = df.iloc[top_indices]

    # Return only needed fields, and replace NaNs for frontend safety
    return recommendations[['title', 'location', 'company_name', 'salary', 'deadline']].fillna('')


@app.route('/api/recommend-jobs', methods=['POST'])
def get_job_recommendations():
    user_input = request.json.get('profile')
    if not user_input:
        return jsonify({'error': 'Please provide user profile text'}), 400

    try:
        results = recommend_jobs(user_input)
        return jsonify(results.to_dict(orient='records')), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/joblistingdetail', methods=['GET'])
def get_job_listing():
    job_id = request.args.get('id')  # Get job ID from the query string (e.g., ?id=1)

    if job_id:
        try:
            # Connect to the database
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)

            # Fetch job details by job_id
            cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
            job = cursor.fetchone()

            if job:
                # Return job details as JSON
                return jsonify(job)
            else:
                return jsonify({"error": "Job not found"}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    else:
        return jsonify({"error": "Job ID is required"}), 400

@app.route('/job-detail')
def jobdetail():
    job_id = request.args.get('id')  # Get job ID from the query string (e.g., ?id=123)

    if job_id:
        try:
            # Connect to the database
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)

            # Fetch job details by job_id
            cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
            job = cursor.fetchone()

            if job:
                # Pass job details to the template
                return render_template('job-detail.html', job=job)
            else:
                return "Job not found", 404

        except Exception as e:
            return str(e), 500
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    else:
        return "Job ID is required", 400

@app.route('/category')
def category():
    return render_template('category.html')

@app.route('/')
def login_page():
    if 'user_id' not in session:
        return redirect("/login")
    return render_template('index.html')

@app.route('/form')
def form():
    return render_template('form.html')
@app.route('/postjob')
def postjob():
    return render_template('postjob.html')
@app.route('/forgotpassword')
def forgotpassword():
    return render_template('forgotpassword.html')
@app.route('/adminpanel')
def adminpanel():
    return render_template('adminpanel.html')
@app.route('/users')
def users():
    return render_template('users.html')
@app.route('/chat')
def chat():
    return render_template('chat.html')
@app.route('/404')
def error():
    return render_template('404.html')
@app.route('/showbookmarkedjobs')
def bookmarkedjob():
    return render_template('bookmarkedjob.html')
@app.route('/joblist')
def listjob():
    return render_template('joblist.html')
@app.route('/contact_save', methods=['GET', 'POST'])
def contact_save():
    if request.method == 'POST':
        name = request.form.get('name')        # ✅ FIXED
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        # Insert the form data into the database
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO contact_queries (name, email, subject, message)
                VALUES (%s, %s, %s, %s)
            """, (name, email, subject, message))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'message': 'Your message has been sent successfully!'}), 200
        except mysql.connector.Error as err:
            return jsonify({'error': f'Error: {err}'}), 500

    return render_template('contact.html')


@app.route('/adminlogin')
def adminlogin():
    session.clear()
    return render_template('adminlogin.html')
def get_table_count(table_name):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        return count
    except Exception as e:
        print(f"Error counting {table_name}: {e}")
        return 0
    finally:
        if conn:
            conn.close()

@app.route('/api/accepted_job')
def accepted_jobs():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not logged in'}), 401

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Fetch jobs that this user applied to and were accepted
        query = """
SELECT a.*, j.* 
FROM job_applications a
JOIN jobs j ON a.job_id = j.id
WHERE a.user_id = %s

        """
        cursor.execute(query, (user_id,))
        jobs = cursor.fetchall()

        return jsonify(jobs)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

@app.route('/api/recent-applications')
def recent_applications():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT name, submitted_at,status,id
            FROM job_applications
            ORDER BY submitted_at DESC
            LIMIT 5
        """)
        return jsonify(cursor.fetchall())
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()
@app.route('/api/recent-requests')
def recent_requests():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT job_id, status, created_at
            FROM requests
            ORDER BY created_at DESC
            LIMIT 5
        """)
        return jsonify(cursor.fetchall())
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admins-count')
def admins_count():
    return jsonify({'count': get_table_count('admins')})

@app.route('/api/bookmarks-count')
def bookmarks_count():
    return jsonify({'count': get_table_count('bookmark')})

@app.route('/api/job-applications-count')
def job_applications_count():
    return jsonify({'count': get_table_count('job_applications')})

@app.route('/api/job-reviews-count')
def job_reviews_count():
    return jsonify({'count': get_table_count('job_reviews')})

@app.route('/api/jobs-count')
def jobs_count():
    return jsonify({'count': get_table_count('jobs')})

@app.route('/api/messages-count')
def messages_count():
    return jsonify({'count': get_table_count('messages')})

@app.route('/api/profiles-count')
def profiles_count():
    return jsonify({'count': get_table_count('profiles')})

@app.route('/api/requests-count')
def requests_count():
    return jsonify({'count': get_table_count('requests')})

@app.route('/api/users-count')
def users_count():
    return jsonify({'count': get_table_count('users')})
@app.route('/admin_register', methods=['POST'])
def admin_register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['confirm_password']

    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400

    hashed_password = generate_password_hash(password)

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Optional: check if user already exists
        cursor.execute("SELECT * FROM admins WHERE username = %s OR email = %s", (username, email))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'error': 'Username or email already exists'}), 409

        cursor.execute(
            "INSERT INTO admins (username, email, password) VALUES (%s, %s, %s)", 
            (username, email, hashed_password)
        )
        conn.commit()
        return jsonify({'message': 'Registration successful'}), 201

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/admin_login', methods=['POST'])
def admin_login():
    username = request.form['username']
    password = request.form['password']

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM admins WHERE username=%s", (username,))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()

    if admin and check_password_hash(admin['password'], password):
        session.permanent = True  # Set session to permanent so it lasts longer
        session['admin_id'] = admin['id']
        session['admin_username'] = admin['username']
        return redirect('/adminpanel')
    else:
        return "Invalid credentials", 401



@app.route('/profile/<int:user_id>', methods=['GET'])
def get_profile(user_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM profiles WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return jsonify(user)
@app.route('/userslist')
def userslist():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM profiles')
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({'users': users})
# Route to handle sending requests
@app.route('/api/submit_review', methods=['POST'])
def submit_review():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'User not logged in'}), 401

    data = request.json
    job_id = data.get('job_id')
    rating = data.get('rating')
    review = data.get('review')
    user_name = session['username']

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    query = "INSERT INTO job_reviews (job_id, user_name, rating, review) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (job_id, user_name, rating, review))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'success': True})

@app.route('/api/job_reviews')
def job_reviews():
    job_id = request.args.get('job_id')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT user_name, rating, review, created_at FROM job_reviews WHERE job_id = %s ORDER BY created_at DESC", (job_id,))
    reviews = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify(reviews)

def build_query(filters):
    query = "SELECT * FROM jobs WHERE 1=1"
    
    # Apply filters
    if filters.get('category'):
        query += " AND category = %s"
    
    if filters.get('location'):
        query += " AND location = %s"
    
    if filters.get('job_type'):
        query += " AND job_type = %s"
    
    if filters.get('keyword'):
        query += " AND (title LIKE %s OR description LIKE %s)"
    
    query += " ORDER BY id DESC"
    
    return query

# API endpoint to fetch jobs with filters
@app.route('/api/search-jobs', methods=['GET'])
def get_filtered_jobs():
    filters = {
        'category': request.args.get('category'),
        'location': request.args.get('location'),
        'job_type': request.args.get('job_type'),
        'keyword': request.args.get('keyword')
    }

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    # Build the query based on the filters
    query = build_query(filters)

    # Prepare parameters for the query
    params = []
    if filters['category']:
        params.append(filters['category'])
    if filters['location']:
        params.append(filters['location'])
    if filters['job_type']:
        params.append(filters['job_type'])
    if filters['keyword']:
        params.extend([f"%{filters['keyword']}%", f"%{filters['keyword']}%"])
    
    cursor.execute(query, tuple(params))
    jobs = cursor.fetchall()
    cursor.close()
    
    return jsonify(jobs)

@app.route('/chat_users')
def chat_users():
    admin_id = session.get('admin_id')
    user_id = session.get('user_id')

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    if admin_id:
        # Admin is logged in: fetch users assigned to this admin
        cursor.execute("""
            SELECT u.id, u.username
            FROM users u
            JOIN requests r ON u.id = r.user_id
            WHERE r.admin_id = %s AND r.status = 'accepted'
        """, (admin_id,))
        users = cursor.fetchall()

        response = [
            {'id': u['id'], 'username': u['username'], 'is_online': True} for u in users
        ]

    elif user_id:
        # User is logged in: fetch admins assigned to this user
        cursor.execute("""
            SELECT a.id, a.username
            FROM admins a
            JOIN requests r ON a.id = r.admin_id
            WHERE r.user_id = %s AND r.status = 'accepted'
        """, (user_id,))
        admins = cursor.fetchall()

        response = [
            {'id': a['id'], 'username': a['username'], 'is_online': True} for a in admins
        ]
    else:
        conn.close()
        return redirect('/login')  # No one is logged in

    cursor.close()
    conn.close()
    return jsonify({'users': response})


@app.route('/get_messages/<int:user_id>')
def get_messages(user_id):
    admin_id = session.get('admin_id')
    logged_in_user_id = session.get('user_id')

    if not admin_id and not logged_in_user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    if admin_id:
        # Admin is viewing chat with a specific user (user_id)
        cursor.execute("""
            SELECT sender_type, sender_id, receiver_id, content, timestamp
            FROM messages
            WHERE (sender_id = %s AND receiver_id = %s AND sender_type = 'user')
               OR (sender_id = %s AND receiver_id = %s AND sender_type = 'admin')
            ORDER BY timestamp
        """, (user_id, admin_id, admin_id, user_id))

    elif logged_in_user_id:
        # User is chatting with admin (assuming single admin with ID = 1)
        admin_id = 1
        if user_id != admin_id:
            return jsonify({'error': 'Invalid access'}), 403

        cursor.execute("""
            SELECT sender_type, sender_id, receiver_id, content, timestamp
            FROM messages
            WHERE (sender_id = %s AND receiver_id = %s AND sender_type = 'user')
               OR (sender_id = %s AND receiver_id = %s AND sender_type = 'admin')
            ORDER BY timestamp
        """, (logged_in_user_id, admin_id, admin_id, logged_in_user_id))

    messages = cursor.fetchall()
    cursor.close()
    conn.close()

    formatted = []
    for msg in messages:
        is_sender = (
            (admin_id and msg['sender_type'] == 'admin' and msg['sender_id'] == admin_id) or
            (logged_in_user_id and msg['sender_type'] == 'user' and msg['sender_id'] == logged_in_user_id)
        )

        formatted.append({
            'sender_type': msg['sender_type'],
            'sender_id': msg['sender_id'],
            'receiver_id': msg['receiver_id'],
            'content': msg['content'],
            'timestamp': msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'sender_name': 'You' if is_sender else 'Other'
        })

    return jsonify({'messages': formatted})
@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    content = data.get('content')
    receiver_id = data.get('receiver_id')

    admin_id = session.get('admin_id')
    user_id = session.get('user_id')

    if not content or not receiver_id:
        return jsonify({'error': 'Invalid data'}), 400

    if not admin_id and not user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    sender_type = 'admin' if admin_id else 'user'
    sender_id = admin_id if admin_id else user_id

    # Optional: prevent users from sending to users or admins from sending to admins
    if sender_type == 'user' and receiver_id != 1:
        return jsonify({'error': 'Users can only send to admin'}), 403
    if sender_type == 'admin':
        # You may want to check if receiver_id is a valid user if needed
        pass

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO messages (sender_type, sender_id, receiver_id, content, timestamp)
        VALUES (%s, %s, %s, %s, NOW())
    """, (sender_type, sender_id, receiver_id, content))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'success': True})


@app.route('/logout')
def logout():
    session.clear()  # Clears the session
    return redirect('/login')



@app.route('/api/category-vacancies')
def get_category_vacancies():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT category, COUNT(*) as vacancy_count 
        FROM jobs 
        GROUP BY category
    """)
    data = cursor.fetchall()
    cursor.close()
    return jsonify(data)


if __name__ == '__main__':
    init_db() 
    app.run(debug=True)
