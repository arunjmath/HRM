from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import certifi
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from routes.mail_service import send_contact_email 

from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "aarav_people_partners_secret_2024")
UPLOAD_FOLDER = "static/uploads/resumes"

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)



# MongoDB connection
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://kpery669_db_user:2unxvgw9xizGCC9N@cluster0.hoyzybd.mongodb.net/?retryWrites=true&w=majority",
)
client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
)
db = client["aarav_people_partners"]

# Collections
contacts_col = db["contacts"]
jobs_col = db["jobs"]
applications_col = db["applications"]
blogs_col = db["blogs"]
testimonials_col = db["testimonials"]
courses_col = db["courses"]
enrollments_col = db["enrollments"]
admins_col = db["admins"]
newsletter_col = db["newsletter"]


# ── Admin Auth ──────────────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please login to access admin panel.", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# ── Public Routes ────────────────────────────────────────────────────────────
@app.route("/")
def index():
    testimonials = list(testimonials_col.find({"active": True}).limit(6))
    blogs = list(blogs_col.find({"published": True}).sort("created_at", -1).limit(3))
    jobs = list(jobs_col.find({"active": True}).limit(4))
    courses = list(courses_col.find({"active": True}).limit(3))
    return render_template("index.html", testimonials=testimonials, blogs=blogs, jobs=jobs, courses=courses)

@app.route("/about-us")
def about():
    return render_template("about.html")

# Services
@app.route("/manpower-payroll-outsourcing")
def manpower():
    return render_template("services/manpower.html")

@app.route("/hr-consulting")
def hr_consulting():
    return render_template("services/hr_consulting.html")

@app.route("/talent-acquisition")
def talent_acquisition():
    return render_template("services/talent_acquisition.html")

@app.route("/hr-payroll-training")
def hr_training():
    return render_template("services/hr_training.html")

# Careers / Jobs
@app.route("/careers")
def careers():
    search = request.args.get("search", "")
    location = request.args.get("location", "")
    department = request.args.get("department", "")
    query = {"active": True}
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    if department:
        query["department"] = department
    jobs = list(jobs_col.find(query).sort("created_at", -1))
    departments = jobs_col.distinct("department", {"active": True})
    return render_template("careers.html", jobs=jobs, departments=departments,
                           search=search, location=location, department=department)

@app.route("/careers/<job_id>")
def job_detail(job_id):
    job = jobs_col.find_one({"_id": ObjectId(job_id)})
    if not job:
        flash("Job not found.", "error")
        return redirect(url_for("careers"))
    return render_template("job_detail.html", job=job)
def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# =========================
# APPLY JOB ROUTE
# =========================

@app.route("/careers/<job_id>/apply", methods=["GET", "POST"])
def apply_job(job_id):

    job = jobs_col.find_one({"_id": ObjectId(job_id)})

    if not job:
        return redirect(url_for("careers"))

    if request.method == "POST":

        # =========================
        # RESUME FILE
        # =========================

        resume = request.files.get("resume")

        resume_filename = ""

        if resume and resume.filename != "":

            if allowed_file(resume.filename):

                filename = secure_filename(resume.filename)

                # Unique filename
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"

                file_path = os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )

                resume.save(file_path)

                resume_filename = filename

            else:
                flash(
                    "Only PDF, DOC, and DOCX files are allowed.",
                    "danger"
                )

                return redirect(request.url)

        # =========================
        # APPLICATION DATA
        # =========================

        application = {

            "job_id": job_id,

            "job_title": job["title"],

            "name": request.form.get("name"),

            "email": request.form.get("email"),

            "phone": request.form.get("phone"),

            "experience": request.form.get("experience"),

            "cover_letter": request.form.get("cover_letter"),

            # Saved uploaded file
            "resume_file": resume_filename,

            "status": "pending",

            "applied_at": datetime.now()
        }

        applications_col.insert_one(application)

        flash(
            "Application submitted successfully! We'll be in touch soon.",
            "success"
        )

        return redirect(url_for("careers"))

    return render_template("apply.html", job=job)
# Student Courses
@app.route("/student-course")
def student_course():
    courses = list(courses_col.find({"active": True}))
    return render_template("student_course.html", courses=courses)

@app.route("/course/<course_id>")
def course_detail(course_id):
    course = courses_col.find_one({"_id": ObjectId(course_id)})
    if not course:
        return redirect(url_for("student_course"))
    return render_template("course_detail.html", course=course)

@app.route("/course/<course_id>/enroll", methods=["GET", "POST"])
def enroll_course(course_id):
    course = courses_col.find_one({"_id": ObjectId(course_id)})
    if not course:
        return redirect(url_for("student_course"))
    if request.method == "POST":
        enrollment = {
            "course_id": course_id,
            "course_name": course["title"],
            "name": request.form.get("name"),
            "email": request.form.get("email"),
            "phone": request.form.get("phone"),
            "qualification": request.form.get("qualification"),
            "message": request.form.get("message", ""),
            "status": "pending",
            "enrolled_at": datetime.now()
        }
        enrollments_col.insert_one(enrollment)
        flash("Enrollment request submitted! Our team will contact you shortly.", "success")
        return redirect(url_for("student_course"))
    return render_template("enroll.html", course=course)

# Testimonials
@app.route("/testimonials")
def testimonials():
    items = list(testimonials_col.find({"active": True}))
    return render_template("testimonials.html", testimonials=items)

# Blog
@app.route("/blog")
def blog():
    blogs = list(blogs_col.find({"published": True}).sort("created_at", -1))
    return render_template("blog.html", blogs=blogs)

@app.route("/blog/<slug>")
def blog_detail(slug):
    post = blogs_col.find_one({"slug": slug, "published": True})
    if not post:
        return redirect(url_for("blog"))
    # increment views
    blogs_col.update_one({"_id": post["_id"]}, {"$inc": {"views": 1}})
    recent = list(blogs_col.find({"published": True, "_id": {"$ne": post["_id"]}})
                  .sort("created_at", -1).limit(3))
    return render_template("blog_detail.html", post=post, recent=recent)

# Contact
# Contact
@app.route("/contact-us", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        contact_data = {
            "name": request.form.get("name"),
            "email": request.form.get("email"),
            "phone": request.form.get("phone"),
            "company": request.form.get("company", ""),
            "service": request.form.get("service"),
            "message": request.form.get("message"),
            "status": "new",
            "created_at": datetime.now()
        }

        # Save to MongoDB
        contacts_col.insert_one(contact_data)

        # Send Email
        send_contact_email(contact_data)

        flash("Thank you! We'll get back to you within 24 hours.", "success")

        return redirect(url_for("contact"))

    return render_template("contact.html")

# Newsletter
@app.route("/newsletter/subscribe", methods=["POST"])
def newsletter_subscribe():
    email = request.form.get("email") or request.json.get("email")
    if email:
        existing = newsletter_col.find_one({"email": email})
        if not existing:
            newsletter_col.insert_one({"email": email, "subscribed_at": datetime.now()})
            return jsonify({"success": True, "message": "Subscribed successfully!"})
        return jsonify({"success": False, "message": "Already subscribed."})
    return jsonify({"success": False, "message": "Invalid email."})

# ── ADMIN ROUTES ─────────────────────────────────────────────────────────────
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        admin = admins_col.find_one({"username": username})
        if admin and check_password_hash(admin["password"], password):
            session["admin_logged_in"] = True
            session["admin_name"] = admin.get("name", "Admin")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid credentials.", "error")
    return render_template("admin/login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

@app.route("/admin")
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    stats = {
        "contacts": contacts_col.count_documents({}),
        "new_contacts": contacts_col.count_documents({"status": "new"}),
        "jobs": jobs_col.count_documents({"active": True}),
        "applications": applications_col.count_documents({}),
        "new_applications": applications_col.count_documents({"status": "pending"}),
        "blogs": blogs_col.count_documents({"published": True}),
        "courses": courses_col.count_documents({"active": True}),
        "enrollments": enrollments_col.count_documents({}),
        "testimonials": testimonials_col.count_documents({}),
        "newsletter": newsletter_col.count_documents({}),
    }
    recent_contacts = list(contacts_col.find().sort("created_at", -1).limit(5))
    recent_applications = list(applications_col.find().sort("applied_at", -1).limit(5))
    return render_template("admin/dashboard.html", stats=stats,
                           recent_contacts=recent_contacts,
                           recent_applications=recent_applications)

# Admin – Jobs
@app.route("/admin/jobs")
@admin_required
def admin_jobs():
    jobs = list(jobs_col.find().sort("created_at", -1))
    return render_template("admin/jobs.html", jobs=jobs)

@app.route("/admin/jobs/new", methods=["GET", "POST"])
@admin_required
def admin_new_job():
    if request.method == "POST":
        job = {
            "title": request.form.get("title"),
            "department": request.form.get("department"),
            "location": request.form.get("location"),
            "type": request.form.get("type"),
            "experience": request.form.get("experience"),
            "salary": request.form.get("salary", ""),
            "description": request.form.get("description"),
            "requirements": request.form.get("requirements"),
            "benefits": request.form.get("benefits", ""),
            "active": True,
            "created_at": datetime.now()
        }
        jobs_col.insert_one(job)
        flash("Job posted successfully!", "success")
        return redirect(url_for("admin_jobs"))
    return render_template("admin/job_form.html", job=None)

@app.route("/admin/jobs/<job_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_job(job_id):
    job = jobs_col.find_one({"_id": ObjectId(job_id)})
    if request.method == "POST":
        jobs_col.update_one({"_id": ObjectId(job_id)}, {"$set": {
            "title": request.form.get("title"),
            "department": request.form.get("department"),
            "location": request.form.get("location"),
            "type": request.form.get("type"),
            "experience": request.form.get("experience"),
            "salary": request.form.get("salary", ""),
            "description": request.form.get("description"),
            "requirements": request.form.get("requirements"),
            "benefits": request.form.get("benefits", ""),
            "active": request.form.get("active") == "on"
        }})
        flash("Job updated!", "success")
        return redirect(url_for("admin_jobs"))
    return render_template("admin/job_form.html", job=job)

@app.route("/admin/jobs/<job_id>/delete", methods=["POST"])
@admin_required
def admin_delete_job(job_id):
    jobs_col.delete_one({"_id": ObjectId(job_id)})
    flash("Job deleted.", "success")
    return redirect(url_for("admin_jobs"))

# Admin – Applications
@app.route("/admin/applications")
@admin_required
def admin_applications():
    apps = list(applications_col.find().sort("applied_at", -1))
    return render_template("admin/applications.html", applications=apps)

@app.route("/admin/applications/<app_id>/status", methods=["POST"])
@admin_required
def admin_update_application(app_id):
    status = request.form.get("status")
    applications_col.update_one({"_id": ObjectId(app_id)}, {"$set": {"status": status}})
    flash("Application status updated.", "success")
    return redirect(url_for("admin_applications"))

# Admin – Contacts
@app.route("/admin/contacts")
@admin_required
def admin_contacts():
    contacts = list(contacts_col.find().sort("created_at", -1))
    return render_template("admin/contacts.html", contacts=contacts)

@app.route("/admin/contacts/<contact_id>/status", methods=["POST"])
@admin_required
def admin_update_contact(contact_id):
    status = request.form.get("status")
    contacts_col.update_one({"_id": ObjectId(contact_id)}, {"$set": {"status": status}})
    return redirect(url_for("admin_contacts"))

# Admin – Blogs
@app.route("/admin/blogs")
@admin_required
def admin_blogs():
    blogs = list(blogs_col.find().sort("created_at", -1))
    return render_template("admin/blogs.html", blogs=blogs)

@app.route("/admin/blogs/new", methods=["GET", "POST"])
@admin_required
def admin_new_blog():
    if request.method == "POST":
        import re, unicodedata
        title = request.form.get("title")
        slug = re.sub(r'[^\w\s-]', '', unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode()).strip().lower()
        slug = re.sub(r'[-\s]+', '-', slug)
        blog = {
            "title": title,
            "slug": slug,
            "author": request.form.get("author", session.get("admin_name")),
            "category": request.form.get("category"),
            "excerpt": request.form.get("excerpt"),
            "content": request.form.get("content"),
            "image_url": request.form.get("image_url", ""),
            "published": request.form.get("published") == "on",
            "views": 0,
            "created_at": datetime.now()
        }
        blogs_col.insert_one(blog)
        flash("Blog post created!", "success")
        return redirect(url_for("admin_blogs"))
    return render_template("admin/blog_form.html", blog=None)

@app.route("/admin/blogs/<blog_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_blog(blog_id):
    blog = blogs_col.find_one({"_id": ObjectId(blog_id)})
    if request.method == "POST":
        blogs_col.update_one({"_id": ObjectId(blog_id)}, {"$set": {
            "title": request.form.get("title"),
            "author": request.form.get("author"),
            "category": request.form.get("category"),
            "excerpt": request.form.get("excerpt"),
            "content": request.form.get("content"),
            "image_url": request.form.get("image_url", ""),
            "published": request.form.get("published") == "on"
        }})
        flash("Blog updated!", "success")
        return redirect(url_for("admin_blogs"))
    return render_template("admin/blog_form.html", blog=blog)

@app.route("/admin/blogs/<blog_id>/delete", methods=["POST"])
@admin_required
def admin_delete_blog(blog_id):
    blogs_col.delete_one({"_id": ObjectId(blog_id)})
    flash("Blog deleted.", "success")
    return redirect(url_for("admin_blogs"))

# Admin – Courses
@app.route("/admin/courses")
@admin_required
def admin_courses():
    courses = list(courses_col.find().sort("created_at", -1))
    return render_template("admin/courses.html", courses=courses)

@app.route("/admin/courses/new", methods=["GET", "POST"])
@admin_required
def admin_new_course():
    if request.method == "POST":
        course = {
            "title": request.form.get("title"),
            "category": request.form.get("category"),
            "duration": request.form.get("duration"),
            "level": request.form.get("level"),
            "price": request.form.get("price"),
            "description": request.form.get("description"),
            "curriculum": request.form.get("curriculum"),
            "image_url": request.form.get("image_url", ""),
            "certification": request.form.get("certification", ""),
            "active": True,
            "created_at": datetime.now()
        }
        courses_col.insert_one(course)
        flash("Course created!", "success")
        return redirect(url_for("admin_courses"))
    return render_template("admin/course_form.html", course=None)

@app.route("/admin/courses/<course_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_course(course_id):
    course = courses_col.find_one({"_id": ObjectId(course_id)})
    if request.method == "POST":
        courses_col.update_one({"_id": ObjectId(course_id)}, {"$set": {
            "title": request.form.get("title"),
            "category": request.form.get("category"),
            "duration": request.form.get("duration"),
            "level": request.form.get("level"),
            "price": request.form.get("price"),
            "description": request.form.get("description"),
            "curriculum": request.form.get("curriculum"),
            "image_url": request.form.get("image_url", ""),
            "certification": request.form.get("certification", ""),
            "active": request.form.get("active") == "on"
        }})
        flash("Course updated!", "success")
        return redirect(url_for("admin_courses"))
    return render_template("admin/course_form.html", course=course)

# Admin – Enrollments
@app.route("/admin/enrollments")
@admin_required
def admin_enrollments():
    enrollments = list(enrollments_col.find().sort("enrolled_at", -1))
    return render_template("admin/enrollments.html", enrollments=enrollments)

# Admin – Testimonials
@app.route("/admin/testimonials")
@admin_required
def admin_testimonials():
    items = list(testimonials_col.find().sort("created_at", -1))
    return render_template("admin/testimonials.html", testimonials=items)

@app.route("/admin/testimonials/new", methods=["GET", "POST"])
@admin_required
def admin_new_testimonial():
    if request.method == "POST":
        t = {
            "name": request.form.get("name"),
            "designation": request.form.get("designation"),
            "company": request.form.get("company", ""),
            "rating": int(request.form.get("rating", 5)),
            "message": request.form.get("message"),
            "image_url": request.form.get("image_url", ""),
            "active": True,
            "created_at": datetime.now()
        }
        testimonials_col.insert_one(t)
        flash("Testimonial added!", "success")
        return redirect(url_for("admin_testimonials"))
    return render_template("admin/testimonial_form.html", testimonial=None)

@app.route("/admin/testimonials/<t_id>/toggle", methods=["POST"])
@admin_required
def admin_toggle_testimonial(t_id):
    t = testimonials_col.find_one({"_id": ObjectId(t_id)})
    testimonials_col.update_one({"_id": ObjectId(t_id)}, {"$set": {"active": not t.get("active", True)}})
    return redirect(url_for("admin_testimonials"))

@app.route("/admin/testimonials/<t_id>/delete", methods=["POST"])
@admin_required
def admin_delete_testimonial(t_id):
    testimonials_col.delete_one({"_id": ObjectId(t_id)})
    flash("Testimonial deleted.", "success")
    return redirect(url_for("admin_testimonials"))

# Admin – Newsletter
@app.route("/admin/newsletter")
@admin_required
def admin_newsletter():
    subscribers = list(newsletter_col.find().sort("subscribed_at", -1))
    return render_template("admin/newsletter.html", subscribers=subscribers)

# ── Seed Data / Setup ────────────────────────────────────────────────────────
@app.route("/setup/init", methods=["GET"])
def setup_init():
    """One-time setup endpoint to seed default admin and sample data."""
    # Create default admin
    if not admins_col.find_one({"username": "admin"}):
        admins_col.insert_one({
            "username": "admin",
            "password": generate_password_hash("Admin@1234"),
            "name": "Site Admin",
            "email": "admin@aaravpeoplepartners.com",
            "created_at": datetime.now()
        })

    # Seed sample jobs
    if jobs_col.count_documents({}) == 0:
        jobs_col.insert_many([
            {"title": "HR Manager", "department": "Human Resources", "location": "Bengaluru",
             "type": "Full-time", "experience": "3-5 years", "salary": "6-10 LPA",
             "description": "We are looking for an experienced HR Manager...",
             "requirements": "MBA in HR, 3+ years experience, Strong communication skills",
             "benefits": "Health insurance, PF, Gratuity", "active": True, "created_at": datetime.now()},
            {"title": "Payroll Specialist", "department": "Finance", "location": "Bengaluru",
             "type": "Full-time", "experience": "2-4 years", "salary": "4-7 LPA",
             "description": "Looking for a Payroll Specialist with strong accounting knowledge...",
             "requirements": "B.Com/M.Com, Tally knowledge, Payroll software experience",
             "benefits": "Health insurance, PF", "active": True, "created_at": datetime.now()},
            {"title": "Talent Acquisition Executive", "department": "Recruitment", "location": "Bengaluru",
             "type": "Full-time", "experience": "1-3 years", "salary": "3-5 LPA",
             "description": "We need a dynamic recruiter to source and place top talent...",
             "requirements": "Any graduate, Recruitment experience preferred",
             "benefits": "Health insurance, Incentives", "active": True, "created_at": datetime.now()},
        ])

    # Seed sample courses
    if courses_col.count_documents({}) == 0:
        courses_col.insert_many([
            {"title": "HR & Payroll Management", "category": "HR", "duration": "3 Months",
             "level": "Beginner to Advanced", "price": "15,000",
             "description": "Comprehensive HR & Payroll course covering all aspects...",
             "curriculum": "Module 1: HR Fundamentals\nModule 2: Payroll Processing\nModule 3: Compliance & Labour Laws",
             "image_url": "", "certification": "NSQF Level 5", "active": True, "created_at": datetime.now()},
            {"title": "Talent Acquisition & Recruitment", "category": "Recruitment", "duration": "6 Weeks",
             "level": "Intermediate", "price": "8,000",
             "description": "Master the art of talent sourcing and recruitment...",
             "curriculum": "Module 1: Job Analysis\nModule 2: Sourcing Strategies\nModule 3: Interview Techniques",
             "image_url": "", "certification": "Certificate of Completion", "active": True, "created_at": datetime.now()},
            {"title": "E-Commerce Manager", "category": "E-Commerce", "duration": "4 Months",
             "level": "Intermediate to Advanced", "price": "20,000",
             "description": "Industry-aligned program for managerial roles in digital commerce...",
             "curriculum": "Module 1: E-Commerce Fundamentals\nModule 2: AI in E-Commerce\nModule 3: Team Management",
             "image_url": "", "certification": "NSQF Level 6", "active": True, "created_at": datetime.now()},
        ])

    # Seed testimonials
    if testimonials_col.count_documents({}) == 0:
        testimonials_col.insert_many([
            {"name": "Priya Sharma", "designation": "HR Manager", "company": "TechCorp Bengaluru",
             "rating": 5, "message": "Aarav People Partners transformed our HR operations completely. Highly recommend their payroll outsourcing services!",
             "image_url": "", "active": True, "created_at": datetime.now()},
            {"name": "Rahul Verma", "designation": "CEO", "company": "StartupHub",
             "rating": 5, "message": "Excellent talent acquisition team. They found us the perfect candidates within a week!",
             "image_url": "", "active": True, "created_at": datetime.now()},
            {"name": "Ananya Nair", "designation": "Student", "company": "",
             "rating": 5, "message": "The HR & Payroll course gave me the skills I needed to land my dream job. Thank you Aarav People Partners!",
             "image_url": "", "active": True, "created_at": datetime.now()},
        ])

    return jsonify({"status": "success", "message": "Database initialized! Admin: admin / Admin@1234"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)