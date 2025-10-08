# app.py
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from PSG_stuff import *  # or your own builder that writes to disk
import io
import os

app = Flask(__name__)

# Subject -> topic options (used by the front-end JS to populate the datalist)
SUBJECT_TOPICS = {
    "Math":   ['Algebra',
               'Advanced Math',
               'Problem-Solving and Data Analysis',
               'Geometry and Trigonometry'],
    "Verbal": ['Information and Ideas', 
               'Craft and Structure',
               'Expression of Ideas',
               'Standard English Conventions']
}

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        student_name = request.form["student_name"].strip()
        desired_subject = request.form["desired_subject"].strip()

        # Comma-separated from the tag selector hidden input
        topics_raw = request.form.get("desired_topics", "")
        desired_topics = [t.strip() for t in topics_raw.split(",") if t.strip()]

        # Ensure integer
        try:
            desired_question_amount = int(request.form["desired_question_amount"])
        except (KeyError, ValueError):
            desired_question_amount = 0

        # TODO: Build your per-selection PDF list here (example placeholder)
        
        if len(desired_topics) > 0:
            generate_practice_set(student_name, desired_subject, desired_question_amount, desired_topics)
        else:
            generate_practice_set(student_name, desired_subject, desired_question_amount)

        return send_file(
            f"generated_practice_set.pdf",
            as_attachment=True,
            download_name=f"generated_practice_set.pdf",
            mimetype="application/pdf"
        )

    # GET: render form, provide both the options list and the mapping
    return render_template(
        "index.html",
        subject_options=list(SUBJECT_TOPICS.keys()),
        subject_topics=SUBJECT_TOPICS
    )

if __name__ == "__main__":
    # For local dev; use a proper WSGI server in production
    app.run(debug=True)
