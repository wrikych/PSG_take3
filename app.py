# app.py
from flask import Flask, render_template, request, send_file, abort
from werkzeug.utils import secure_filename
import os
import traceback

app = Flask(__name__)

SUBJECT_TOPICS = {
    "Math": ['Algebra', 'Advanced Math', 'Problem-Solving and Data Analysis', 'Geometry and Trigonometry'],
    "Verbal": ['Information and Ideas', 'Craft and Structure', 'Expression of Ideas', 'Standard English Conventions']
}

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Lazy import to keep baseline memory low
        from PSG_stuff import generate_practice_set

        student_name = request.form["student_name"].strip()
        desired_subject = request.form["desired_subject"].strip()

        topics_raw = request.form.get("desired_topics", "")
        desired_topics = [t.strip() for t in topics_raw.split(",") if t.strip()]

        try:
            desired_question_amount = int(request.form["desired_question_amount"])
        except (KeyError, ValueError):
            return abort(400, description="Invalid question amount")

        # Call generator; it should write under /tmp and RETURN the final PDF path
        out_path = generate_practice_set(
            student_name,
            desired_subject,
            desired_question_amount,
            desired_topics if desired_topics else None
        )

        if not out_path or not os.path.exists(out_path):
            return abort(500, description="Failed to generate PDF")

        download_name = f"{secure_filename(student_name) or 'practice'}_{desired_subject}_Practice.pdf"
        return send_file(out_path, as_attachment=True, download_name=download_name, mimetype="application/pdf")

    # GET
    return render_template(
        "index.html",
        subject_options=list(SUBJECT_TOPICS.keys()),
        subject_topics=SUBJECT_TOPICS
    )

@app.get("/healthz")
def healthz():
    return "ok", 200

# Optional: log unexpected errors so they show up in Heroku logs
@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error("Unhandled error: %s\n%s", e, traceback.format_exc())
    return ("Internal Server Error", 500)

if __name__ == "__main__":
    app.run(debug=True)
