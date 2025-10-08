# helper_psg.py  (your helper script, updated for Heroku/Render/etc.)

import os
import io
import csv
import time
import base64
import random
import pathlib
import tempfile

import numpy as np
import pandas as pd
import pikepdf

from sqlalchemy import create_engine, text, bindparam
from urllib.parse import quote_plus

# Selenium bits (works locally and on Heroku with buildpacks)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


# ---------------------------
# Constants / DB connection
# ---------------------------

appearances_list = [
    '902D LOWER', '903D MEDIUM', '1000D LOWER', '1000D UPPER', '902D UPPER',
    '1000D MEDIUM', '903D LOWER', '902D MEDIUM', '903D UPPER', '901D UPPER',
    '904D LOWER', '901D LOWER', '904D MEDIUM', '904D UPPER', '901D MEDIUM',
    'BB3 UPPER', 'BB5 MEDIUM', 'BB9 MEDIUM', 'BB10 MEDIUM', 'BB4 MEDIUM',
    'BB5 UPPER', 'BB2 UPPER', 'BB2 LOWER', 'BB9 UPPER', 'BB4 LOWER',
    'BB6 MEDIUM', 'BB8 UPPER', 'BB2 MEDIUM', 'BB10 LOWER', 'BB1 MEDIUM',
    'BB1 UPPER', 'BB10 UPPER', 'BB5 LOWER', 'BB4 UPPER', 'BB7 LOWER',
    'BB6 LOWER', 'BB8 MEDIUM', 'BB3 LOWER', 'BB6 UPPER', 'BB8 LOWER',
    'BB7 UPPER', 'BB3 MEDIUM', 'BB7 MEDIUM', 'BB9 LOWER', 'BB1 LOWER',
    'LT9_Module2', 'LT9_Module1', 'LT10_Module1', 'LT4_Module1', 'LT8_Module1',
    'LT3_Module2', 'LT7_Module1', 'LT6_Module1', 'LT2_Module2', 'LT2_Module1',
    'LT8_Module2', 'LT4_Module2', 'LT3_Module1', 'LT6_Module2', 'LT10_Module2',
    'LT5_Module1', 'LT7_Module2', 'LT1_Module1', 'LT5_Module2', 'LT1_Module2'
]

USER = 'portalmycramcrew_ro'
PWD  = quote_plus("Cr@mCrew!123")
HOST = 'mycramcrew.com'
PORT = 3306
DB   = 'portalmycramcrew_live'

engine = create_engine(f"mysql+pymysql://{USER}:{PWD}@{HOST}:{PORT}/{DB}?charset=utf8mb4")


# ---------------------------
# Utility paths
# ---------------------------

HERE = pathlib.Path(__file__).resolve().parent
# local_db.csv should live alongside this file (commit it to the repo)
LOCAL_DB_CSV = HERE / 'local_db.csv'


# ---------------------------
# Core data pulls / transforms
# ---------------------------

def create_student_data(FULL_NAME: str) -> pd.DataFrame:
    full_name_param = bindparam('fullName')
    query = text("""
        SELECT DISTINCT
            first_name, last_name, event_date, module_name, subject, sort_order,
            primary_class_cd_desc, skill_desc, questionId, difficulty, question_type,
            student_answer, time_spent_seconds, is_correct_answer
        FROM user_dsat_practice_test 
        JOIN user 
          ON user_dsat_practice_test.fk_student_user_id = user.user_id
        JOIN dsat_practice_test 
          ON user_dsat_practice_test.fk_dsat_practice_test_id = dsat_practice_test.dsat_practice_test_id 
        JOIN user_event 
          ON user_dsat_practice_test.fk_user_event_id = user_event.user_event_id 
        JOIN user_dsat_practice_test_answer_sheet  
          ON user_dsat_practice_test.user_dsat_practice_test_id = user_dsat_practice_test_answer_sheet.fk_user_dsat_practice_test_id 
        JOIN blue_book_question_header 
          ON user_dsat_practice_test_answer_sheet.question_uid = blue_book_question_header.uId 
        JOIN dsat_test_module_questions 
          ON user_dsat_practice_test_answer_sheet.question_uid = dsat_test_module_questions.fk_bluebook_question_uid 
        JOIN dsat_test_module 
          ON dsat_test_module_questions.fk_dsat_test_module_id = dsat_test_module.dsat_test_module_id 
        WHERE CONCAT(first_name, " ", last_name) = :fullName
    """).bindparams(full_name_param)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"fullName": FULL_NAME})


def fix_modules(student: pd.DataFrame) -> pd.DataFrame:
    mods_dict = student.groupby('module_name').size().to_dict()
    mods_to_delete = []
    for mod, count in mods_dict.items():
        if 'Math' in mod:
            if count != 22:
                mods_to_delete.append(mod)
        elif 'Verbal' in mod:
            if count != 27:
                mods_to_delete.append(mod)
    return student[~student['module_name'].isin(mods_to_delete)]


def filter_desired_content(student: pd.DataFrame, subject=None, topic_list=None) -> pd.DataFrame:
    if subject:
        student = student[student['subject'] == subject]
    if topic_list:
        student = student[student['primary_class_cd_desc'].isin(topic_list)]
    return student


def get_importance_index(subset: pd.DataFrame) -> float:
    count = np.log1p(subset.shape[0])
    Y = subset[subset['is_correct_answer'] == 'Y'].shape[0]
    N = subset[subset['is_correct_answer'] == 'N'].shape[0]
    acc = Y / (Y + N) if (Y + N) else 0.0
    avg_time = float(subset['time_spent_seconds'].mean() or 0.0)
    # Map difficulty letters to numbers if necessary
    diff_map = {'E': 1, 'M': 2, 'H': 3}
    diff = subset['difficulty'].map(diff_map).fillna(subset['difficulty']).astype(float)
    avg_diff = float(diff.mean() or 0.0)
    return (1 - acc) * avg_time * count * (4 - avg_diff)


def cycle_through_subtopics(main_df: pd.DataFrame) -> dict:
    res = {}
    for val, subset in main_df.groupby('skill_desc'):
        res[val] = get_importance_index(subset)
    return res


def find_dict_sum(d: dict) -> int:
    return int(sum(d.values()))


def get_question_amounts(resultant_dict: dict, number_of_questions: int = 30) -> dict:
    total = sum(resultant_dict.values()) or 1.0
    weights = {k: v / total for k, v in sorted(resultant_dict.items(), key=lambda kv: kv[1], reverse=True)}
    alloc = {k: int(w * number_of_questions) for k, w in weights.items()}
    return alloc


def instantiate_pool(subject: str) -> pd.DataFrame:
    if not LOCAL_DB_CSV.exists():
        raise FileNotFoundError(f"local_db.csv not found at {LOCAL_DB_CSV}. Commit it to the repo.")
    local_db = pd.read_csv(LOCAL_DB_CSV)
    # compute total appearances per row
    local_db['total_appearances'] = local_db[appearances_list].sum(axis=1)
    available = local_db[local_db['total_appearances'] == 0]
    if subject in ('Math', 'Verbal'):
        available = available[available['subject'] == subject]
    return available


def get_selected_questions(amounts_dict: dict, pool_df: pd.DataFrame, target_amount: int = 30) -> list:
    target_ids = []
    # Top off allocation to reach target_amount
    keys = list(amounts_dict.keys())
    i = 0
    while find_dict_sum(amounts_dict) < target_amount and keys:
        k = keys[i % len(keys)]
        amounts_dict[k] += 1
        i += 1
    # Sample from each pool (guard against small pools)
    for k, size in amounts_dict.items():
        pool = list(pd.unique(pool_df.loc[pool_df['skill_desc'] == k, 'questionId']))
        if not pool:
            continue
        take = min(len(pool), int(size))
        target_ids.extend(random.sample(pool, take))
    # If still short, fill from global pool (optional)
    short = target_amount - len(target_ids)
    if short > 0 and not pool_df.empty:
        global_pool = list(pd.unique(pool_df['questionId']))
        extra = min(short, len(global_pool))
        target_ids.extend(random.sample(global_pool, extra))
    return target_ids


def pull_questionDetailsFromDB(target_ids: list) -> pd.DataFrame:
    ids_param = bindparam("ids", expanding=True)
    query = text("""
        SELECT 
            ROW_NUMBER() OVER (ORDER BY questionId) AS sort_order,
            questionId, prompt, body, stem, stimulus,
            choice_a, choice_b, choice_c, choice_d,
            d.correct_choice, rationale
        FROM blue_book_question_header h 
        JOIN blue_book_question_details d ON h.uId = d.uId 
        WHERE fk_dsat_question_usage_type_id < 3
          AND questionId IN :ids
    """).bindparams(ids_param)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"ids": list(target_ids)})


# ---------------------------
# Rendering (HTML -> PDF)
# ---------------------------

def refined_math(input_file: str, output_file: str, title: str) -> None:
    """CSV -> HTML (no Windows-local font URLs)."""
    with open(input_file, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
        rows = list(reader)

    def clean(val: str) -> str:
        if val is None: return ""
        v = str(val).strip()
        return "" if v == "" or v.lower() == "na" else v

    questions_html = ""
    for i, row in enumerate(rows, 1):
        qid = clean(row.get('sort_order', '')) or i
        try:
            qid = int(float(str(qid)))
        except Exception:
            qid = i
        qval = clean(row.get('questionId', ''))
        prompt = clean(row.get('prompt', ''))
        stem   = clean(row.get('stem', ''))
        body   = clean(row.get('body', ''))
        stim   = clean(row.get('stimulus', ''))
        rationale = clean(row.get('rationale', ''))
        correct   = clean(row.get('correct_choice', '')).upper()

        choices = {
            'A': clean(row.get('choice_a', '')),
            'B': clean(row.get('choice_b', '')),
            'C': clean(row.get('choice_c', '')),
            'D': clean(row.get('choice_d', '')),
        }
        choices = {k: v for k, v in choices.items() if v}

        questions_html += f"""
        <div class="question">
          <div class="question-id">Question {qid} ({qval})</div>
          {f'<div class="prompt">{prompt}</div>' if prompt else ''}
          {f'<div class="stem">{stem}</div>' if stem else ''}
          {f'<div class="body">{body}</div>' if body else ''}
          {f'<div class="stem">{stim}</div>' if stim else ''}"""

        if choices:
            questions_html += """<div class="choices">"""
            for letter, textv in choices.items():
                questions_html += f"""
              <div class="choice">
                <div class="choice-letter">({letter})</div>
                <div class="choice-text">{textv}</div>
              </div>"""
            questions_html += "</div>"
        else:
            questions_html += """<div class="free-response"></div>"""

        if rationale:
            questions_html += f"""<div class="rationale"><strong>Rationale:</strong> {rationale}</div>"""

        questions_html += "</div>"

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <link href="https://fonts.cdnfonts.com/css/sofia-pro" rel="stylesheet">
  <link href="https://fonts.cdnfonts.com/css/sharp-sans" rel="stylesheet">
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
  <style>
      body {{
          font-family: 'Sofia Pro', -apple-system, sans-serif;
          font-size: 12pt; line-height: 1.5;
          max-width: 900px; margin: 0 auto; padding: 25px 0.8cm;
      }}
      h1, h2, h3, h4, .page-title {{ font-family: "Sharp Sans", Arial, sans-serif; font-weight:700; }}
      html, body {{ font-synthesis: none; }}
      .page-title {{
        display:block; font-family:'Sharp Sans', sans-serif; font-size:21pt; font-weight:800;
        text-align:center; color:#000; margin:0 0 40px 0; padding-bottom:10px; border-bottom:2px solid #000;
      }}
      .prompt {{ font-weight: 500; margin-bottom: 12px; }}
      .choices {{ margin-left: 30px; }}
      .choice {{ display:flex; margin-bottom:8px; align-items:baseline; }}
      .choice-letter {{ min-width:25px; font-weight:700; }}
      .choice-text {{ flex:1; }}
      .rationale {{ margin-top: 15px; padding-top: 10px; }}
      .question {{ margin-bottom:30px; padding-bottom:20px; break-inside:avoid; }}
  </style>
</head>
<body>
    <div class="page-title">{title}</div>
    {questions_html}
</body>
</html>
"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_template)


def _make_chrome_driver() -> webdriver.Chrome:
    """Create a Chrome driver that works locally and on Heroku.
    For Heroku, add buildpacks:
      1) heroku/python
      2) https://github.com/heroku/heroku-buildpack-google-chrome
      3) https://github.com/heroku/heroku-buildpack-chromedriver
    """
    chrome_bin = os.environ.get("GOOGLE_CHROME_BIN")
    driver_path = os.environ.get("CHROMEDRIVER_PATH")

    opts = Options()
    if chrome_bin:
        opts.binary_location = chrome_bin
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--allow-file-access-from-files")
    opts.add_argument("--force-device-scale-factor=1")

    if driver_path and os.path.exists(driver_path):
        service = Service(executable_path=driver_path)
        return webdriver.Chrome(service=service, options=opts)
    # Fallback: chromedriver in PATH (local dev)
    return webdriver.Chrome(options=opts)


def html_to_pdf_math_enhanced(html_file: str, output_pdf: str) -> None:
    """Convert HTML -> PDF via Chrome DevTools printToPDF."""
    driver = _make_chrome_driver()
    try:
        file_url = pathlib.Path(html_file).resolve().as_uri()
        driver.get(file_url)

        # Wait for MathJax (if present)
        driver.execute_script("""
            if (typeof MathJax !== 'undefined' && MathJax.typesetPromise) {
                return MathJax.typesetPromise();
            }
            return null;
        """)
        # Ensure fonts are loaded
        driver.execute_script("return document.fonts && document.fonts.ready && document.fonts.ready.then(() => true)")
        time.sleep(0.1)

        # Strongly suggest Sharp Sans on headings
        driver.execute_script("""
          const css = `
            h1, h2, h3, h4, .title, .page-title, #title,
            header h1, header .title, svg text, .mjx-svg text, .mjx-svg-text {
              font-family: "Sharp Sans", Arial, sans-serif !important;
              font-weight: 700 !important;
            }`;
          const tag = document.createElement('style');
          tag.textContent = css;
          document.head.appendChild(tag);
        """)

        print_options = {
            'landscape': False,
            'printBackground': True,
            'preferCSSPageSize': False,
            'paperWidth': 8.5, 'paperHeight': 11,
            'marginTop': 0.5, 'marginBottom': 0.5, 'marginLeft': 0.75, 'marginRight': 0.75,
            'scale': 1.0
        }
        result = driver.execute_cdp_cmd('Page.printToPDF', print_options)
        with open(output_pdf, 'wb') as f:
            f.write(base64.b64decode(result['data']))
    finally:
        driver.quit()


def merge_pdfs(pdf_files: list, output_path: str) -> str:
    """Merge PDFs to output_path (absolute) and return output_path."""
    out = pikepdf.Pdf.new()
    for pdf_file in pdf_files:
        with pikepdf.open(pdf_file) as pdf:
            out.pages.extend(pdf.pages)
    out.save(output_path)
    return output_path


# ---------------------------
# Orchestrator (now returns final PDF path)
# ---------------------------

def generate_practice_set(student_name: str,
                          desired_subject: str,
                          desired_question_amount: int,
                          desired_topics: list | None = None,
                          workdir: str | None = None) -> str:
    """
    Build practice set entirely under a writable temp dir and return the final PDF absolute path.
    """
    workdir = workdir or tempfile.mkdtemp(prefix="psg_")  # e.g., /tmp/psg_abcd1234
    q_csv   = os.path.join(workdir, 'ws_questions.csv')
    s_csv   = os.path.join(workdir, 'ws_solutions.csv')
    q_html  = os.path.join(workdir, 'ws_questions.html')
    s_html  = os.path.join(workdir, 'ws_solutions.html')
    q_pdf   = os.path.join(workdir, 'ws_questions.pdf')
    s_pdf   = os.path.join(workdir, 'ws_solutions.pdf')
    out_pdf = os.path.join(workdir, 'generated_practice_set.pdf')

    # Pipeline (same logic, different paths)
    student_info = create_student_data(student_name)
    student_info = fix_modules(student_info)
    student_info = filter_desired_content(student_info, subject=desired_subject, topic_list=desired_topics)
    subs_dict    = cycle_through_subtopics(student_info)
    q_amounts    = get_question_amounts(subs_dict, number_of_questions=int(desired_question_amount))
    pool_df      = instantiate_pool(desired_subject)
    selected_ids = get_selected_questions(q_amounts, pool_df, target_amount=int(desired_question_amount))
    worksheet_df = pull_questionDetailsFromDB(selected_ids)

    # Write intermediates into /tmp
    worksheet_df.to_csv(s_csv, index=False)
    worksheet_df.drop(columns=['correct_choice', 'rationale'], errors='ignore').to_csv(q_csv, index=False)

    # HTML -> PDF (in /tmp)
    refined_math(q_csv, q_html, f'{student_name} : {desired_subject} Practice Set')
    html_to_pdf_math_enhanced(q_html, q_pdf)

    refined_math(s_csv, s_html, f'{student_name} : {desired_subject} Practice Set Solutions')
    html_to_pdf_math_enhanced(s_html, s_pdf)

    # Merge and return final path
    return merge_pdfs([q_pdf, s_pdf], out_pdf)
