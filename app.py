from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
import logging
from bson import ObjectId
import os
import datetime
from werkzeug.utils import secure_filename

# Set up logging
logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client['job_easy']
collection = db['user']
collection_hr=db['hr']
collection_jobs=db['job']
application_collection = db['applications']


# File upload setup
UPLOAD_FOLDER = os.path.join('static', 'resumes')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register_hr', methods=['POST'])
def register_hr():
    fullname = request.form.get('fullname')
    email = request.form.get('email')
    country_code = request.form.get('countryCode')
    phone = request.form.get('phone')
    password = request.form.get('password')
    confirm_password = request.form.get('confirmPassword')
    status = request.form.get('company')

    # Debugging: Log the incoming data
    app.logger.debug(f"Registering reqruiter: {fullname}, {email}, {phone}")

    # Check if the user already exists
    existing_user = collection_hr.find_one({'$or': [{'email': email}, {'phone': phone}]})
    if existing_user:
        app.logger.debug(f"User already exists with email: {email} or phone: {phone}")
        return redirect(url_for('login'))

    # Check if passwords match
    if password != confirm_password:
        app.logger.warning("Passwords do not match!")
        return "Passwords do not match!", 400

    # Create a new user
    new_user = {
        "fullname": fullname,
        "email": email,
        "phone": f"{country_code}{phone}",
        "password": password,
        "status": status
    }

    # Insert the user into MongoDB
    result = collection_hr.insert_one(new_user)
    user_id = str(result.inserted_id)
    app.logger.debug(f"New user created with email: {email}")
    return redirect(url_for('login', user_id=user_id))
@app.route('/register', methods=['POST'])
def register():
    fullname = request.form.get('fullname')
    email = request.form.get('email')
    country_code = request.form.get('countryCode')
    phone = request.form.get('phone')
    password = request.form.get('password')
    confirm_password = request.form.get('confirmPassword')
    status = request.form.get('status_work')

    # Debugging: Log the incoming data
    app.logger.debug(f"Registering user: {fullname}, {email}, {phone}")

    # Check if the user already exists
    existing_user = collection.find_one({'$or': [{'email': email}, {'phone': phone}]})
    if existing_user:
        app.logger.debug(f"User already exists with email: {email} or phone: {phone}")
        return redirect(url_for('login'))

    # Check if passwords match
    if password != confirm_password:
        app.logger.warning("Passwords do not match!")
        return "Passwords do not match!", 400

    # Create a new user
    new_user = {
        "fullname": fullname,
        "email": email,
        "phone": f"{country_code}{phone}",
        "password": password,
        "status": status
    }

    # Insert the user into MongoDB
    result = collection.insert_one(new_user)
    user_id = str(result.inserted_id)
    app.logger.debug(f"New user created with email: {email}")
    return redirect(url_for('login', user_id=user_id))

@app.route('/login_hr', methods=['GET', 'POST'])
def login_hr():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        app.logger.debug(f"Attempting login with email: {email}")

        # Check if the user exists with the given credentials
        user = collection_hr.find_one({"email": email, "password": password})

        if user:
            user_id = str(user['_id'])
            return redirect(url_for('home_hr', user_id=user_id))
        else:
            app.logger.warning(f"Login failed for user: {email}")
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        app.logger.debug(f"Attempting login with email: {email}")

        # Check if the user exists with the given credentials
        user = collection.find_one({"email": email, "password": password})

        if user:
            user_id = str(user['_id'])
            return redirect(url_for('home', user_id=user_id))
        else:
            app.logger.warning(f"Login failed for user: {email}")
            return redirect(url_for('login'))
    
    return render_template('login.html')
@app.route('/home_hr')
def home_hr():
    user_id = request.args.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = collection_hr.find_one({"_id": ObjectId(user_id)})
    if not user:
        return "User not found", 404

    # Fetch all jobs posted by this recruiter
    jobs = list(collection_jobs.find({"user_id": user_id}))

    # For each job, fetch applicants
    for job in jobs:
        job_id = str(job['_id'])
        applications = list(application_collection.find({"job_id": job_id}))
        applicants = []
        for app in applications:
            applicant = collection.find_one({"_id": ObjectId(app['user_id'])})
            if applicant:
                applicants.append({
                    "fullname": applicant.get("fullname"),
                    "email": applicant.get("email"),
                    "phone": applicant.get("phone"),
                    "status": applicant.get("status"),
                    "resume": applicant.get("resume"),
                    "applied_at": app.get("applied_at")
                })
        job['applicants'] = applicants

    return render_template('home_hr.html', user=user, jobs=jobs)


    

@app.route('/home', methods=['GET', 'POST'])
def home():
    user_id = request.args.get('user_id')
    if not user_id:
        return redirect(url_for('login'))  # Redirect to login if no user_id

    user = collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        return "User not found", 404  # Return an error if user is not found

    # Get filter values from the form
    title_filter = request.form.get('title')
    experience_filter = request.form.get('experience')
    location_filter = request.form.get('location')

    # Build the query for job search
    query = {}

    if title_filter:
        query['title'] = {'$regex': title_filter, '$options': 'i'}  # Case-insensitive match
    if experience_filter:
        query['experience'] = experience_filter
    if location_filter:
        query['location'] = location_filter

    # Fetch filtered jobs from the database
    jobs = list(collection_jobs.find(query))  # Apply the query to find matching jobs

    return render_template('home.html', user=user, jobs=jobs)



@app.route('/profile', methods=["GET", "POST"])
def profile():
    if request.method == "GET":
        user_id = request.args.get('user_id')
        user = collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return "User not found", 404
        return render_template('profile.html', user=user)

    if request.method == "POST":
        user_id = request.form.get('user_id')
        fullname = request.form.get('fullname')
        phone = request.form.get('phone')
        status = request.form.get('status')

        user = collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return "User not found", 404

        # Handling resume upload
        resume_path = user.get('resume')
        resume = request.files.get('resume')
        if resume and resume.filename != "":
            filename = secure_filename(resume.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume.save(file_path)
            resume_path = f"resumes/{filename}"

        # Handling certifications
        certifications = []
        index = 0
        while True:
            cert_name = request.form.get(f'certifications[{index}][name]')
            cert_details = request.form.get(f'certifications[{index}][details]')
            cert_date = request.form.get(f'certifications[{index}][issued_date]')

            if not cert_name:  # Exit loop when no more inputs
                break

            certifications.append({
                "name": cert_name,
                "details": cert_details,
                "issued_date": cert_date
            })
            index += 1

        # Handling projects
        projects = []
        project_index = 0
        while True:
            heading = request.form.get(f'projects[{project_index}][heading]')
            summary = request.form.get(f'projects[{project_index}][summary]')
            link = request.form.get(f'projects[{project_index}][link]')
            skills = request.form.get(f'projects[{project_index}][skills]')

            if not heading:  # Exit loop when no more inputs
                break

            projects.append({
                "heading": heading,
                "summary": summary,
                "link": link,
                "skills": skills
            })
            project_index += 1

        # Update the user document
        collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "fullname": fullname,
                    "phone": phone,
                    "status": status,
                    "resume": resume_path,
                    "certifications": certifications,
                    "projects": projects
                }
            }
        )

        return redirect(url_for('home', user_id=user_id))
@app.route('/post_job', methods=['POST'])
def post_job():
    title = request.form.get('title')
    description = request.form.get('description')
    location = request.form.get('location')
    user_id = request.form.get('user_id')

    new_job = {
        "title": title,
        "description": description,
        "location": location,
        "user_id": user_id
    }

    result=collection_jobs.insert_one(new_job)
    app.logger.debug(f"User  applied for job {result}")

    return redirect(url_for('home_hr', user_id=user_id))
@app.route('/apply_job', methods=['POST'])
def apply_job():
    job_id = request.form.get('job_id')
    user_id = request.form.get('user_id')
    app.logger.debug(f"job_id: {job_id}, user_id: {user_id}")
    if not job_id or not user_id:
        return "Job ID or User ID is missing", 400

    # Check if job and user exist
    job = collection_jobs.find_one({"_id": ObjectId(job_id)})
    user = collection.find_one({"_id": ObjectId(user_id)})

    if not job:
        return "Job not found", 404
    if not user:
        return "User not found", 404

    # Save the application to the database
    application = {
        "user_id": user_id,
        "job_id": job_id,
        "status": "Applied",  # You can modify this as needed
        "applied_at": datetime.datetime.now()
    }

    # Assuming there's an applications collection for job applications
    application_collection.insert_one(application)

    app.logger.debug(f"User {user_id} applied for job {job_id} with details: {application}")

    # Redirect back to the job list or show a success message
    return redirect(url_for('home', user_id=user_id))  # You could re

@app.route('/profile_hr', methods=["GET", "POST"])
def profile_hr():
    if request.method == "GET":
        user_id = request.args.get('user_id')
        user = collection_hr.find_one({"_id": ObjectId(user_id)})
        if not user:
            return "User not found", 404
        return render_template('hr_profile.html', user=user)
    if request.method == "POST":
        user_id = request.form.get('user_id')
        fullname = request.form.get('fullname')
        phone = request.form.get('phone')
        company=request.form.get('company')
        website=request.form.get('website')
        linkedin=request.form.get('linkedin')
        industry=request.form.get('industry')
        company_location=request.form.get('company_location')
        company_size=request.form.get('company_size')



        user = collection_hr.find_one({"_id": ObjectId(user_id)})
        if not user:
            return "User not found", 404

        
        
        # Update the user document
        collection_hr.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "fullname": fullname,
                    "phone": phone,
                    "company":company,
                    "website":website,
                    "linkedin":linkedin,
                    "industry":industry,
                    "company_location":company_location,
                    "company_size":company_size,
                }
            }
        )

        return redirect(url_for('home_hr', user_id=user_id))


if __name__ == '__main__':
    app.run(debug=True)
