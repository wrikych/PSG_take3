import numpy as np
import pandas as pd
import time

import pikepdf

import csv
from bs4 import BeautifulSoup, NavigableString, Comment
import numpy as np
import pandas as pd
import re
from html import unescape


import time, pathlib

import base64
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PyPDF2 import PdfMerger
import re

from transcription_data import *
from regex_stuff import * 

import warnings

def insert_colon(text):
    # Look for the words "Exercise" or "Practice" and insert a colon before them
    return re.sub(r"\b(Exercise|Practice)\b", r": \1", text)

def make_dicts():    
    alg_dict = {}
    adv_dict = {}
    psda_dict = {}
    gtrig_dict = {}
    
    for item in alg_items:
        alg_dict[item] = insert_colon(item)
    for item in adv_items:
        adv_dict[item] = insert_colon(item)
    for item in psda_items:
        psda_dict[item] = insert_colon(item)
    for item in gtrig_items:
        gtrig_dict[item] = insert_colon(item)
    
    return alg_dict, adv_dict, psda_dict, gtrig_dict

def refined_math(input_file, output_file, title):
    print("convert convert convert ! ! !  (X L)")

    # Read the CSV file
    with open(input_file, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
        rows = list(reader)

    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <link href="https://fonts.cdnfonts.com/css/sofia-pro" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
  <style>
      body {{
          font-family: 'Sofia Pro', -apple-system, sans-serif;
          font-size: 12pt;
          font-weight: 400;
          line-height: 1.5;
          max-width: 900px;
          margin: 0 auto;
          padding: 25px 0.8cm; /* match 0.8cm margin sides */
      }}
      /* === Sharp Sans local mappings (Windows local files) === */
      /* Book / Regular (400) */
      @font-face {{
        font-family: "Sharp Sans";
        src:
          local("Sharp Sans Book"),
          local("SharpSans-Book"),
          url("file:///C:/Users/wriky/Downloads/Sharp%20Type%20Order%20%23ST-256723031/Sharp%20Sans/TTF-Windows/SharpSans-Book.ttf") format("truetype");
        font-weight: 400;
        font-style: normal;
        font-display: swap;
      }}
      /* Bold (700) */
      @font-face {{
        font-family: "Sharp Sans";
        src:
          local("Sharp Sans Bold"),
          local("SharpSans-Bold"),
          url("file:///C:/Users/wriky/Downloads/Sharp%20Type%20Order%20%23ST-256723031/Sharp%20Sans/TTF-Windows/SharpSans-Bold.ttf") format("truetype");
        font-weight: 700;
        font-style: normal;
        font-display: swap;
      }}
      /* ExtraBold (800) */
      @font-face {{
        font-family: "Sharp Sans";
        src:
          local("Sharp Sans ExtraBold"),
          local("SharpSans-ExtraBold"),
          local("SharpSans-Extrabold"),
          url("file:///C:/Users/wriky/Downloads/Sharp%20Type%20Order%20%23ST-256723031/Sharp%20Sans/TTF-Windows/SharpSans-ExtraBold.ttf") format("truetype");
        font-weight: 800;
        font-style: normal;
        font-display: swap;
      }}
      h1, h2, h3, h4, .page-title {{
        font-family: "Sharp Sans", Arial, sans-serif;
        font-weight: 700;
      }}
      html, body {{ font-synthesis: none; }}
      .header-title {{
          font-family: 'Sharp Sans', sans-serif;
          font-size: 2.5rem;
          font-weight: 700;
          text-align: center;
          margin: 20px 0 40px 0;
          letter-spacing: -0.5px;
      }}
      .prompt {{ font-weight: 500; margin-bottom: 12px; }}
      .choices {{ margin-left: 30px; }}
      .choice {{
          display: flex;
          margin-bottom: 8px;
          align-items: baseline;
      }}
      .choice-letter {{ min-width: 25px; font-weight: 700; }}
      .choice-text {{ flex: 1; }}
      .rationale {{
          font-family: 'Sofia Pro', sans-serif;
          font-weight: 300;
          margin-top: 15px;
          padding-top: 10px;
          border-top: none;
      }}
      .question {{
          margin-bottom: 30px;
          padding-bottom: 20px;
          border: none;
          page-break-inside: avoid;
          break-inside: avoid;
          display: block;
      }}
      .page-title {{
        display: block;
        font-family: 'Sharp Sans', sans-serif;
        font-size: 21pt;
        font-weight: 800;
        text-align: center;
        color: #000;
        margin: 0 0 40px 0;
        padding-bottom: 10px;
        border-bottom: 2px solid #000;
        background: none;
        box-shadow: none;
      }}

      .question:last-child {{ margin-bottom: 15px; }}
      .question-id {{ font-size: 13pt; font-weight: 600; margin-bottom: 10px; }}
      @media (max-width: 768px) {{
          body {{ padding: 15px 0.8cm; font-size: 11pt; }}
          .header-title {{ margin: 20px 0 30px 0; font-size: 2.2rem; }}
          .choices {{ margin-left: 20px; }}
      }}
  </style>
  

</head>
<body>
    <div class="page-title">{title}</div>
    {questions}
</body>
</html>
"""

    def clean(val: str) -> str:
        if val is None:
            return ""
        v = str(val).strip()
        return "" if v == "" or v.lower() == "na" else v

    questions_html = ""
    for i, row in enumerate(rows, 1):
        qid = int(float(str(clean(row.get('sort_order', ''))).strip()))
        qval = clean(row.get('questionId', ''))
        prompt = clean(row.get('prompt', ''))
        stem = clean(row.get('stem', ''))
        body = clean(row.get('body', ''))
        stim = clean(row.get('stimulus', ''))
        rationale = clean(row.get('rationale', '')) if 'rationale' in row else ""
        correct = clean(row.get('correct_choice', '')).upper()

        choices = {
            'A': row.get('choice_a', '').strip(),
            'B': row.get('choice_b', '').strip(),
            'C': row.get('choice_c', '').strip(),
            'D': row.get('choice_d', '').strip()
        }
        choices = {k: v for k, v in choices.items() if v.lower() != "na" and v.strip() != ""}

        questions_html += f"""
        <div class="question">
          <div class="question-id">Question {qid} ({qval})</div>
          {f'<div class="prompt">{prompt}</div>' if prompt else ''}
          {f'<div class="stem">{stem}</div>' if stem else ''}
          {f'<div class="body">{body}</div>' if body else ''}
          {f'<div class="stem">{stim}</div>' if stim else ''}
          """

        if choices:
            questions_html += """
          <div class="choices">"""
            for letter, text in choices.items():
                questions_html += f"""
            <div class="choice">
                <div class="choice-letter">({letter})</div>
                <div class="choice-text">{text}</div>
            </div>"""
            questions_html += """
          </div>"""
        else:
            questions_html += """
          <div class="free-response"></div>"""
        
        if rationale:
              questions_html += f"""<div class="rationale"><strong>Rationale:</strong> {rationale}</div>"""
        else:
          pass
          

        questions_html += """
        </div>"""  # Removed <hr> so no visible line

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_template.format(title=title, questions=questions_html))

    print(f"Generated adaptive worksheet: {output_file}")


def refined_math_pt2(input_file, output_file, title):
    print("convert convert convert ! ! !  (X L)")

    # Read the CSV file
    with open(input_file, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
        rows = list(reader)

        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <link href="https://fonts.cdnfonts.com/css/sofia-pro" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
  <style>
    /* Page box (print) */
    @page {{
      size: letter;
      margin-top: 0.5in;
      margin-bottom: 0.5in;
      margin-left: 0.8in;
      margin-right: 0.8in;
    }}

    /* Base */
    body {{
      font-family: 'Sofia Pro', -apple-system, sans-serif;
      font-size: 12pt;
      font-weight: 400;
      line-height: 1.6;
      margin: 0;
      padding: 0;
      background: #fff;
      color: #000;
    }}
        /* === Sharp Sans local mappings (Windows local files) ===
   Use file:/// URLs with forward slashes and URL-encoded spaces/#.
*/

/* Book / Regular (400) */
@font-face {{
  font-family: "Sharp Sans";
  src:
    local("Sharp Sans Book"),
    local("SharpSans-Book"),
    url("file:///C:/Users/wriky/Downloads/Sharp%20Type%20Order%20%23ST-256723031/Sharp%20Sans/TTF-Windows/SharpSans-Book.ttf") format("truetype");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}}

/* Bold (700) — FIXED the double %20 in the path */
@font-face {{
  font-family: "Sharp Sans";
  src:
    local("Sharp Sans Bold"),
    local("SharpSans-Bold"),
    url("file:///C:/Users/wriky/Downloads/Sharp%20Type%20Order%20%23ST-256723031/Sharp%20Sans/TTF-Windows/SharpSans-Bold.ttf") format("truetype");
  font-weight: 700;
  font-style: normal;
  font-display: swap;
}}

/* ExtraBold (800) — update filename if yours is Extrabold vs ExtraBold */
@font-face {{
  font-family: "Sharp Sans";
  src:
    local("Sharp Sans ExtraBold"),
    local("SharpSans-ExtraBold"),
    local("SharpSans-Extrabold"),
    url("file:///C:/Users/wriky/Downloads/Sharp%20Type%20Order%20%23ST-256723031/Sharp%20Sans/TTF-Windows/SharpSans-ExtraBold.ttf") format("truetype");
  font-weight: 800;
  font-style: normal;
  font-display: swap;
}}

h1, h2, h3, h4, .page-title {{
  font-family: "Sharp Sans", Arial, sans-serif;
  font-weight: 700; /* or 800 if you want ExtraBold */
}}



/* Prevent faux bold/italic so Chrome must use the real glyphs */
html, body {{ font-synthesis: none; }}


    /* Content wrapper sized to printable width (8.5 - .8 - .8 = 6.9in) */
    .sheet {{
      width: 100%;
      max-width: 6.9in;
      margin: 0 auto;
      padding: 0;                 /* Let @page margins be the gutters */
      box-sizing: border-box;
    }}

    /* Title matches other templates */
    .page-title {{
      display: block;
      font-family: 'Sharp Sans', sans-serif;
      font-size: 30pt;
      font-weight: 800;
      text-align: center;
      color: #000000;
      margin: 0 0 40px 0;
      padding-bottom: 10px;
      border-bottom: 2px solid #000000; /* underline spans .sheet width */
      background: none;
      box-shadow: none;
    }}

    /* Single-column stacked questions */
    .question {{
      display: block;
      margin-bottom: 0.35in;
      padding-bottom: 0.1in;
      border: none;
      page-break-inside: avoid;
      break-inside: avoid;
    }}
    .question:last-child {{
      margin-bottom: 0.2in;
    }}

    .question-id {{
      font-weight: 600;
      margin-bottom: 10px;
    }}

    .prompt {{
      font-weight: 500;
      margin-bottom: 12px;
    }}

    .choices {{
      margin: 0.2in 0 0 0;
      padding-left: 0;
    }}

    /* Works with your .choice-letter + .choice-text structure */
    .choice {{
      display: flex;
      align-items: baseline;
      margin-bottom: 8px;
    }}
    .choice-letter {{
      min-width: 25px;
      font-weight: 600;
    }}
    .choice-text {{
      flex: 1;
    }}

    .rationale {{
      font-family: 'Sofia Pro', sans-serif;
      font-weight: 400;
      margin-top: 15px;
      padding-top: 10px;
      border-top: none;
    }}

    /* Keep media from blowing up layout */
    .question img,
    .question svg {{
      max-width: 100%;
      height: auto;
      display: block;
      page-break-inside: avoid;
      break-inside: avoid;
    }}

    /* Print hardening (avoid shrink-to-fit surprises) */
    @media print {{
      body {{ width: auto; }}
      .sheet {{ max-width: 6.9in; }}
    }}

    /* Print tweaks */
  @media print {{
    body {{ width: auto; }}            /* avoid accidental shrink-to-fit */
    .worksheet {{ max-width: 6.9in; }} /* be explicit for some engines  */
    .question {{ border: none; }}
  }}
  @media screen and (max-width: 768px) {{
  .worksheet {{ max-width: 100%; padding: 15px; }}
  .question-container {{ flex-wrap: wrap; gap: 16px; }}
  .question {{ width: 100%; min-height: auto; }}
  }}
  @media print {{
    .question-container {{
      display: flex;
      flex-wrap: nowrap !important;
      justify-content: space-between;
      width: 100%;
    }}
    .question {{
      flex: 0 0 48% !important;
      max-width: 48% !important;
      border: none;
    }}
  }}
  </style>
</head>
<body>
  <div class="sheet">
    <div class="page-title">{title}</div>
    {questions}
  </div>
</body>
</html>
"""



    questions_html = ""
    for i, row in enumerate(rows, 1):
        question_id = row.get('question_number', str(i)).strip()

        prompt = row.get('prompt', '').strip()
        prompt = '' if prompt.lower() == 'na' else prompt

        stem = row.get('stem', '').strip()
        stem = '' if stem.lower() == 'na' else stem

        body = row.get('body', '').strip()
        body = '' if body.lower() == 'na' else body

        rationale = row.get('rationale', '').strip()
        rationale = '' if rationale.lower() == 'na' else rationale

        choices = {
            'A': row.get('choice_a', '').strip(),
            'B': row.get('choice_b', '').strip(),
            'C': row.get('choice_c', '').strip(),
            'D': row.get('choice_d', '').strip()
        }
        choices = {k: v for k, v in choices.items() if v.lower() != "na" and v.strip() != ""}

        question_html = f"""
        <div class="question">
          <div class="question-id">Question {question_id}</div>
          {f'<div class="prompt">{prompt}</div>' if prompt else ''}
          {f'<div class="stem">{stem}</div>' if stem else ''}
          {f'<div class="body">{body}</div>' if body else ''}"""

        if choices:
            question_html += """
          <div class="choices">"""
            for letter, text in choices.items():
                question_html += f"""
            <div class="choice">
                <div class="choice-letter">{letter}.</div>
                <div class="choice-text">{text}</div>
            </div>"""
            question_html += """
          </div>"""
        else:
            question_html += """
          <div class="free-response"></div>"""

        if rationale:
            question_html += f"""
          <div class="rationale">
              <strong>Rationale:</strong> {rationale}
          </div>"""

        question_html += """
        </div>"""  # close question

        questions_html += question_html

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_template.format(title=title, questions=questions_html))

    print(f"Generated adaptive worksheet: {output_file}")



csv.field_size_limit(131072 * 10)  # 10x the default limit

def clustered_attempt2(input_file, output_file, title, variant="wide"):
    with open(input_file, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    # Choose a body class to activate optional per-doc print tweaks
    body_class = ""
    if variant == "wide":
        body_class = "wide"
    elif variant == "compact":
        body_class = "compact"

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <link href="https://fonts.cdnfonts.com/css/sofia-pro" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
  <style>
    /* Page box (print) */
    @page {{
      size: letter;
      margin-top: 0.5in;
      margin-bottom: 0.5in;
      margin-left: 0.8in;   /* keep left margin for hole punch */
      margin-right: 0.8in;
    }}
    /* Named page for slightly wider right margin (Chrome Print supports this) */
    @page wide {{
      size: letter;
      margin-top: 0.5in;
      margin-bottom: 0.5in;
      margin-left: 0.8in;   /* unchanged */
      margin-right: 0.6in;  /* a bit looser only for 'wide' variant */
    }}
       /* === Sharp Sans local mappings (Windows local files) ===
   Use file:/// URLs with forward slashes and URL-encoded spaces/#.
*/

/* Book / Regular (400) */
@font-face {{
  font-family: "Sharp Sans";
  src:
    local("Sharp Sans Book"),
    local("SharpSans-Book"),
    url("file:///C:/Users/wriky/Downloads/Sharp%20Type%20Order%20%23ST-256723031/Sharp%20Sans/TTF-Windows/SharpSans-Book.ttf") format("truetype");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}}

/* Bold (700) — FIXED the double %20 in the path */
@font-face {{
  font-family: "Sharp Sans";
  src:
    local("Sharp Sans Bold"),
    local("SharpSans-Bold"),
    url("file:///C:/Users/wriky/Downloads/Sharp%20Type%20Order%20%23ST-256723031/Sharp%20Sans/TTF-Windows/SharpSans-Bold.ttf") format("truetype");
  font-weight: 700;
  font-style: normal;
  font-display: swap;
}}

/* ExtraBold (800) — update filename if yours is Extrabold vs ExtraBold */
@font-face {{
  font-family: "Sharp Sans";
  src:
    local("Sharp Sans ExtraBold"),
    local("SharpSans-ExtraBold"),
    local("SharpSans-Extrabold"),
    url("file:///C:/Users/wriky/Downloads/Sharp%20Type%20Order%20%23ST-256723031/Sharp%20Sans/TTF-Windows/SharpSans-ExtraBold.ttf") format("truetype");
  font-weight: 800;
  font-style: normal;
  font-display: swap;
}}
h1, h2, h3, h4, .page-title {{
  font-family: "Sharp Sans", Arial, sans-serif;
  font-weight: 700; /* or 800 if you want ExtraBold */
}}


/* Prevent faux bold/italic so Chrome must use the real glyphs */
html, body {{ font-synthesis: none; }}



    /* Base */
    body {{
      font-family: 'Sofia Pro', -apple-system, sans-serif;
      font-size: 12pt;
      font-weight: 400;
      line-height: 1.6;
      margin: 0;
      padding: 0;
      background: #fff;
      color: #000;
    }}

    /* Content wrapper sized to printable width (8.5 - .8 - .8 = 6.9in) */
    .sheet {{
      width: 100%;
      max-width: 6.9in;      /* default printable width */
      margin: 0 auto;
      padding: 0;
      box-sizing: border-box;
    }}

    /* Title */
    .page-title {{
      display: block;
      font-family: 'Sharp Sans', sans-serif;
      font-size: 21pt;
      font-weight: 800;
      text-align: center;
      color: #000;
      margin: 0 0 40px 0;
      padding-bottom: 10px;
      border-bottom: 2px solid #000;
      background: none;
      box-shadow: none;
    }}

    /* Two-column container (each pair of questions) */
    .question-container {{
      display: flex;
      flex-wrap: nowrap;
      justify-content: space-between;
      width: 100%;
      margin-bottom: 0.5in;
      break-inside: avoid;
      page-break-inside: avoid;
    }}

    .question {{
      flex: 0 0 48%;
      max-width: 48%;
      min-height: 3in;
      text-align: left;
      padding: 10px;
      box-sizing: border-box;
      border: none;
      break-inside: avoid;
      page-break-inside: avoid;
    }}

    .question-id {{ font-weight: 600; margin-bottom: 10px; font-size: 13pt;}}
    .prompt {{ font-weight: 400; margin-bottom: 12px; }}
    .stem, .body {{ margin-bottom: 15px; }}

    .choices {{
      margin: 20px 0 0 0;
      padding-left: 0;
    }}
    .choice {{
      display: flex;
      align-items: baseline;
      margin-bottom: 8px;
      position: relative;
    }}
    /* >>> This renders the "(A) " using your data-letter attribute <<< */
    .choices .choice::before {{
      content: "(" attr(data-letter) ") ";
      font-weight: 700;
      margin-right: 6px;
      white-space: pre;
    }}

    .choice.correct {{ font-weight: 700; }}

    .free-response {{
      margin-top: 20px;
      height: 100px;
      border: none;
    }}

    .rationale {{
      font-family: 'Sofia Pro', sans-serif;
      font-weight: 400;
      margin-top: 15px;
      padding-top: 10px;
      border-top: none;
    }}

    /* Media safety */
    .question img,
    .question svg {{
      max-width: 100%;
      height: auto;
      display: block;
      break-inside: avoid;
      page-break-inside: avoid;
    }}

    /* Print hardening */
    @media print {{
      body {{ width: auto; }}              /* avoid shrink-to-fit surprises */
      .sheet {{ max-width: 6.9in; }}       /* explicit default width */

      /* Activate the named page + a slightly wider content width ONLY in 'wide' mode */
      body.wide {{ page: wide; }}
      body.wide .sheet {{ max-width: 7.1in; }}  /* 8.5 - 0.8 - 0.6 = 7.1in */

      /* Compact mode: subtle tighten for stubborn sets */
      body.compact {{ font-size: 11.5pt; }}
      body.compact .page-title {{ font-size: 28pt; }}
      body.compact .question-container {{ margin-bottom: 0.45in; }}
      body.compact .question {{ padding: 8px; }}
    }}

    /* Screen-only mobile preview (won't affect print) */
    @media screen and (max-width: 768px) {{
      .sheet {{ max-width: 100%; padding: 15px; }}
      .question-container {{ flex-wrap: wrap; gap: 16px; }}
      .question {{ flex: 0 0 100%; max-width: 100%; min-height: auto; }}
      .page-title {{ margin-bottom: 30px; font-size: 26pt; }}
    }}
  </style>
</head>
<body class="{body_class}">
  <div class="sheet">
    <div class="page-title">{title}</div>
    {questions}
  </div>
</body>
</html>
"""

    def clean(val: str) -> str:
        if val is None:
            return ""
        v = str(val).strip()
        return "" if v == "" or v.lower() == "na" else v

    # Build HTML
    questions_html = ""
    question_pairs = [rows[i:i+2] for i in range(0, len(rows), 2)]

    for pair in question_pairs:
        questions_html += '<div class="question-container">'
        for row in pair:
            qid = int(float(str(clean(row.get('sort_order', ''))).strip()))
            qval = clean(row.get('questionId',''))
            prompt = clean(row.get('prompt', ''))
            stem = clean(row.get('stem', ''))
            body_html = clean(row.get('body', ''))

            rationale = clean(row.get('rationale', '')) if 'rationale' in row else ""
            correct = clean(row.get('correct_choice', '')).upper()
            
            if correct not in ("A","B","C","D"):
                correct = ""

            choices_raw = {
                'A': clean(row.get('choice_a', '')),
                'B': clean(row.get('choice_b', '')),
                'C': clean(row.get('choice_c', '')),
                'D': clean(row.get('choice_d', '')),
            }
            choices = {k:v for k,v in choices_raw.items() if v}

            questions_html += f"""
            <div class="question">
              <div class="question-id">Question {qid} ({qval})</div>
              {f'<div class="prompt">{prompt}</div>' if prompt else ''}
              {f'<div class="stem">{stem}</div>' if stem else ''}
              {f'<div class="body">{body_html}</div>' if body_html else ''}"""

            if choices:
                items = []
                for letter, text in choices.items():
                    cls = "choice correct" if letter == correct else "choice"
                    text_html = f"<strong><u>{text}</u></strong>" if letter == correct else text
                    items.append(f'<div class="{cls}" data-letter="{letter}">{text_html}</div>')
                questions_html += f"""
              <div class="choices">
                {''.join(items)}
              </div>"""
            else:
                questions_html += """
              <div class="free-response"></div>"""

            if rationale:
                questions_html += f"""
              <div class="rationale"><strong>Rationale:</strong> {rationale}</div>"""

            questions_html += "</div>"  # .question
        questions_html += "</div>"      # .question-container

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_template.format(title=title, questions=questions_html, body_class=body_class))

    print(f"Generated worksheet ({variant}): {output_file}")

def clustered_attempt3(input_file, output_file, title, variant="wide"):
    with open(input_file, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    # Choose a body class to activate optional per-doc print tweaks
    body_class = ""
    if variant == "wide":
        body_class = "wide"
    elif variant == "compact":
        body_class = "compact"

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <link href="https://fonts.cdnfonts.com/css/sofia-pro" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
  <style>
    /* Page box (print) */
    @page {{
      size: letter;
      margin-top: 0.5in;
      margin-bottom: 0.5in;
      margin-left: 0.8in;   /* keep left margin for hole punch */
      margin-right: 0.8in;
    }}
    /* Named page for slightly wider right margin (Chrome Print supports this) */
    @page wide {{
      size: letter;
      margin-top: 0.5in;
      margin-bottom: 0.5in;
      margin-left: 0.8in;   /* unchanged */
      margin-right: 0.6in;  /* a bit looser only for 'wide' variant */
    }}
       /* === Sharp Sans local mappings (Windows local files) ===
   Use file:/// URLs with forward slashes and URL-encoded spaces/#.
*/

/* Book / Regular (400) */
@font-face {{
  font-family: "Sharp Sans";
  src:
    local("Sharp Sans Book"),
    local("SharpSans-Book"),
    url("file:///C:/Users/wriky/Downloads/Sharp%20Type%20Order%20%23ST-256723031/Sharp%20Sans/TTF-Windows/SharpSans-Book.ttf") format("truetype");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}}

/* Bold (700) — FIXED the double %20 in the path */
@font-face {{
  font-family: "Sharp Sans";
  src:
    local("Sharp Sans Bold"),
    local("SharpSans-Bold"),
    url("file:///C:/Users/wriky/Downloads/Sharp%20Type%20Order%20%23ST-256723031/Sharp%20Sans/TTF-Windows/SharpSans-Bold.ttf") format("truetype");
  font-weight: 700;
  font-style: normal;
  font-display: swap;
}}

/* ExtraBold (800) — update filename if yours is Extrabold vs ExtraBold */
@font-face {{
  font-family: "Sharp Sans";
  src:
    local("Sharp Sans ExtraBold"),
    local("SharpSans-ExtraBold"),
    local("SharpSans-Extrabold"),
    url("file:///C:/Users/wriky/Downloads/Sharp%20Type%20Order%20%23ST-256723031/Sharp%20Sans/TTF-Windows/SharpSans-ExtraBold.ttf") format("truetype");
  font-weight: 800;
  font-style: normal;
  font-display: swap;
}}
h1, h2, h3, h4, .page-title {{
  font-family: "Sharp Sans", Arial, sans-serif;
  font-weight: 700; /* or 800 if you want ExtraBold */
}}


/* Prevent faux bold/italic so Chrome must use the real glyphs */
html, body {{ font-synthesis: none; }}



    /* Base */
    body {{
      font-family: 'Sofia Pro', -apple-system, sans-serif;
      font-size: 12pt;
      font-weight: 400;
      line-height: 1.6;
      margin: 0;
      padding: 0;
      background: #fff;
      color: #000;
    }}

    /* Content wrapper sized to printable width (8.5 - .8 - .8 = 6.9in) */
    .sheet {{
      width: 100%;
      max-width: 6.9in;      /* default printable width */
      margin: 0 auto;
      padding: 0;
      box-sizing: border-box;
    }}

    /* Title */
    .page-title {{
      display: block;
      font-family: 'Sharp Sans', sans-serif;
      font-size: 30pt;
      font-weight: 800;
      text-align: center;
      color: #000;
      margin: 0 0 40px 0;
      padding: 0 12px 10px;          /* small side padding helps measurements */
      border-bottom: 2px solid #000;
      background: none;
      box-shadow: none;

      white-space: nowrap;           /* force single line */
      max-width: 100%;               /* allow full width */
      box-sizing: border-box;        /* include padding in width */
      overflow: visible;             /* don't clip glyphs */
    }}



    /* Two-column container (each pair of questions) */
    .question-container {{
      display: flex;
      flex-wrap: nowrap;
      justify-content: space-between;
      width: 100%;
      margin-bottom: 0.5in;
      break-inside: avoid;
      page-break-inside: avoid;
    }}

    .question {{
      flex: 0 0 48%;
      max-width: 48%;
      min-height: 3in;
      text-align: left;
      padding: 10px;
      box-sizing: border-box;
      border: none;
      break-inside: avoid;
      page-break-inside: avoid;
    }}

    .question-id {{ font-weight: 600; margin-bottom: 10px; font-size: 13pt;}}
    .prompt {{ font-weight: 400; margin-bottom: 12px; }}
    .stem, .body {{ margin-bottom: 15px; }}

    .choices {{
      margin: 20px 0 0 0;
      padding-left: 0;
    }}
    .choice {{
      display: flex;
      align-items: baseline;
      margin-bottom: 8px;
      position: relative;
    }}
    /* >>> This renders the "(A) " using your data-letter attribute <<< */
    .choices .choice::before {{
      content: "(" attr(data-letter) ") ";
      font-weight: 700;
      margin-right: 6px;
      white-space: pre;
    }}

    .choice.correct {{ font-weight: 700; }}

    .free-response {{
      margin-top: 20px;
      height: 100px;
      border: none;
    }}

    .rationale {{
      font-family: 'Sofia Pro', sans-serif;
      font-weight: 400;
      margin-top: 15px;
      padding-top: 10px;
      border-top: none;
    }}

    /* Media safety */
    .question img,
    .question svg {{
      max-width: 100%;
      height: auto;
      display: block;
      break-inside: avoid;
      page-break-inside: avoid;
    }}

    /* Print hardening */
    @media print {{
      body {{ width: auto; }}              /* avoid shrink-to-fit surprises */
      .sheet {{ max-width: 6.9in; }}       /* explicit default width */

      /* Activate the named page + a slightly wider content width ONLY in 'wide' mode */
      body.wide {{ page: wide; }}
      body.wide .sheet {{ max-width: 7.1in; }}  /* 8.5 - 0.8 - 0.6 = 7.1in */

      /* Compact mode: subtle tighten for stubborn sets */
      body.compact {{ font-size: 11.5pt; }}
      body.compact .page-title {{ font-size: 28pt; }}
      body.compact .question-container {{ margin-bottom: 0.45in; }}
      body.compact .question {{ padding: 8px; }}
    }}

    /* Screen-only mobile preview (won't affect print) */
    @media screen and (max-width: 768px) {{
      .sheet {{ max-width: 100%; padding: 15px; }}
      .question-container {{ flex-wrap: wrap; gap: 16px; }}
      .question {{ flex: 0 0 100%; max-width: 100%; min-height: auto; }}
      .page-title {{ margin-bottom: 30px; font-size: 26pt; }}
    }}
  </style>
  
  <script>
  function getNumericPx(v) {{
    const n = parseFloat(v);
    return isNaN(n) ? 0 : n;
  }}

  function availableWidth(el) {{
    // Width the title can actually use inside its parent (minus margins)
    const parent = el.parentElement;
    const pw = parent.getBoundingClientRect().width;

    const cs = getComputedStyle(el);
    const ml = getNumericPx(cs.marginLeft);
    const mr = getNumericPx(cs.marginRight);

    // Because title is box-sizing:border-box, its padding is already included
    // in its own width; we only need to remove horizontal margins from the space it can occupy.
    return Math.max(0, pw - ml - mr);
  }}

  function fits(el, width) {{
    // Use scrollWidth to see if the rendered text spills past the box
    return el.scrollWidth <= width + 0.5; // small fudge for sub-pixel
  }}

  function fitOnOneLine(el, opts) {{
    const maxPt = (opts && opts.maxPt) || 30;
    const minPt = (opts && opts.minPt) || 10; // LOWER MIN to avoid cutoffs
    const steps = (opts && opts.steps) || 22;

    el.style.whiteSpace = 'nowrap';
    el.style.maxWidth = '100%';

    // Start big
    el.style.fontSize = maxPt + 'pt';

    const target = availableWidth(el);
    if (target <= 0) return;

    if (fits(el, target)) return; // fits at max

    // Binary search font-size
    let lo = minPt, hi = maxPt, best = minPt;
    for (let i = 0; i < steps; i++) {{
      const mid = (lo + hi) / 2;
      el.style.fontSize = mid + 'pt';
      if (fits(el, target)) {{
        best = mid; lo = mid;
      }} else {{
        hi = mid;
      }}
      if (Math.abs(hi - lo) < 0.1) break;
    }}
    el.style.fontSize = best + 'pt';

    // LAST-RESORT: if it still doesn't fit at min size, scale it horizontally
    if (!fits(el, target)) {{
      const scale = target / el.scrollWidth;
      el.style.transformOrigin = 'center';
      el.style.display = 'inline-block';
      el.style.transform = 'scale(' + scale + ')';
    }} else {{
      el.style.transform = '';
    }}
  }}

  function runFit() {{
    const el = document.querySelector('.page-title');
    if (!el) return;
    const ready = (document.fonts && document.fonts.ready) ? document.fonts.ready : Promise.resolve();
    ready.then(() => fitOnOneLine(el, {{ maxPt: 30, minPt: 10 }}));
  }}

  document.addEventListener('DOMContentLoaded', runFit);
  window.addEventListener('resize', runFit);

  // Make it print/PDF-aware
  if (window.matchMedia) {{
    const mq = window.matchMedia('print');
    if (mq.addEventListener) {{
      mq.addEventListener('change', e => e.matches ? runFit() : runFit());
    }} else if (mq.addListener) {{
      mq.addListener(() => runFit());
    }}
  }}
  window.addEventListener('beforeprint', runFit);
</script>


</head>
<body class="{body_class}">
  <div class="sheet">
    <div class="page-title">{title}</div>
    {questions}
  </div>
</body>
</html>
"""

    def clean(val: str) -> str:
        if val is None:
            return ""
        v = str(val).strip()
        return "" if v == "" or v.lower() == "na" else v

    # Build HTML
    questions_html = ""
    question_pairs = [rows[i:i+2] for i in range(0, len(rows), 2)]

    for pair in question_pairs:
        questions_html += '<div class="question-container">'
        for row in pair:
            qid = int(float(str(clean(row.get('sort_order', ''))).strip()))
            qval = clean(row.get('questionId',''))
            prompt = clean(row.get('prompt', ''))
            stem = clean(row.get('stem', ''))
            body_html = clean(row.get('body', ''))

            rationale = clean(row.get('rationale', '')) if 'rationale' in row else ""
            correct = clean(row.get('correct_choice', '')).upper()
            
            if correct not in ("A","B","C","D"):
                correct = ""

            choices_raw = {
                'A': clean(row.get('choice_a', '')),
                'B': clean(row.get('choice_b', '')),
                'C': clean(row.get('choice_c', '')),
                'D': clean(row.get('choice_d', '')),
            }
            choices = {k:v for k,v in choices_raw.items() if v}

            questions_html += f"""
            <div class="question">
              <div class="question-id">Question {qid} ({qval})</div>
              {f'<div class="prompt">{prompt}</div>' if prompt else ''}
              {f'<div class="stem">{stem}</div>' if stem else ''}
              {f'<div class="body">{body_html}</div>' if body_html else ''}"""

            if choices:
                items = []
                for letter, text in choices.items():
                    cls = "choice correct" if letter == correct else "choice"
                    text_html = f"<strong><u>{text}</u></strong>" if letter == correct else text
                    items.append(f'<div class="{cls}" data-letter="{letter}">{text_html}</div>')
                questions_html += f"""
              <div class="choices">
                {''.join(items)}
              </div>"""
            else:
                questions_html += """
              <div class="free-response"></div>"""

            if rationale:
                questions_html += f"""
              <div class="rationale"><strong>Rationale:</strong> {rationale}</div>"""

            questions_html += "</div>"  # .question
        questions_html += "</div>"      # .question-container

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_template.format(title=title, questions=questions_html, body_class=body_class))

    print(f"Generated worksheet ({variant}): {output_file}")

def fix_encoding(text):
    if not text:
        return ""
    try:
        return text.encode('latin1').decode('utf-8')
    except:
        return text




def list_pdf_fonts(pdf_path):
    pdf = pikepdf.open(pdf_path)
    seen = set()
    try:
        for page_num, page in enumerate(pdf.pages, 1):
            res = page.get('/Resources')
            if not res:
                continue
            res = dict(res)  # pikepdf.Dictionary -> dict
            fonts = res.get('/Font')
            if not fonts:
                continue
            fonts = dict(fonts)
            for _, font_ref in fonts.items():
                # font_ref may be a direct dict OR an indirect ref
                font_obj = font_ref.get_object() if hasattr(font_ref, 'get_object') else font_ref
                font_obj = dict(font_obj)

                basefont = font_obj.get('/BaseFont')
                subtype  = font_obj.get('/Subtype')
                fam      = font_obj.get('/FontFamily')  # often absent

                # Normalize to strings for display
                basefont_s = str(basefont) if basefont is not None else 'None'
                subtype_s  = str(subtype)  if subtype  is not None else 'None'
                fam_s      = str(fam)      if fam      is not None else 'None'

                key = (basefont_s, subtype_s, fam_s)
                if key not in seen:
                    seen.add(key)
                    print(f"Page {page_num}: BaseFont={basefont_s}, Subtype={subtype_s}, FontFamily={fam_s}")
    finally:
        pdf.close()

    print("\n=== Unique embedded fonts (summary) ===")
    for bf, st, fam in sorted(seen):
        print(f"- BaseFont={bf}, Subtype={st}, FontFamily={fam}")

def make_svg_dict(math_df):
    
    svg_dict = {}
    
    for _, row in math_df.iterrows():
        if "svg" in row['prompt'] or "<img" in row['prompt']:
            svg_dict[row['questionId']] = "PROMPT"
        elif "svg" in row['body'] or "<img" in row['body']:
            svg_dict[row['questionId']] = "BODY"
        elif "svg" in row['stem'] or "<img" in row['stem']:
            svg_dict[row['questionId']] = 'STEM'
        elif "svg" in row['stimulus'] or "<img" in row['stimulus']:
            svg_dict[row['questionId']] = 'STIMULUS'
        else:
            svg_dict[row['questionId']] = 'CLEAN'
    
    math_df['svg_loc'] = [svg_dict[val] for val in math_df['questionId']]
    
    return math_df

def clean_mathJax(input_str): 
     

  if '<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>' in str(input_str):
    new_str = input_str.replace('<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>','')
    return new_str
  else:
    return input_str

def html_to_pdf_math_enhanced(html_file, output_pdf):
    """Convert HTML to PDF with proper MathJax rendering + Sharp Sans title checks."""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')   # new headless is nicer with fonts
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--force-device-scale-factor=1')
    chrome_options.add_argument('--font-render-hinting=none')
    chrome_options.add_argument('--allow-file-access-from-files')

    driver = webdriver.Chrome(options=chrome_options)
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
        # Ensure fonts are fully loaded
        driver.execute_script("return document.fonts.ready && document.fonts.ready.then(() => true)")

        # -------- Check #1: Inject a last-word-wins CSS block to force Sharp Sans on titles
        driver.execute_script("""
          const css = `
            /* take over common title spots (HTML + possible SVG text) */
            h1, h2, h3, h4, .title, .page-title, #title,
            header h1, header .title,
            svg text, .mjx-svg text, .mjx-svg-text {
              font-family: "Sharp Sans", Arial, sans-serif !important;
              font-weight: 700 !important;
            }
            /* catch any inline styles or title-like classes still fighting us */
            [style*="font-family"], [class*="title"] {
              font-family: "Sharp Sans", Arial, sans-serif !important;
            }
          `;
          const tag = document.createElement('style');
          tag.setAttribute('data-injected', 'force-sharp-sans');
          tag.textContent = css;
          document.head.appendChild(tag);
        """)

        # Give the browser a tick to reflow with the injected CSS
        time.sleep(0.1)

        # -------- Check #2: Log what Chrome thinks your title is using
        info = driver.execute_script("""
          function snap(e){
            if(!e) return null;
            const cs = getComputedStyle(e);
            return {
              tag: e.tagName,
              id: e.id || "",
              class: (e.className || "").toString(),
              text: (e.textContent || "").trim().slice(0, 120),
              fontFamily: cs.fontFamily,
              fontWeight: cs.fontWeight,
              fontSize: cs.fontSize
            };
          }
          // Big heading-looking element among h1..h4/.title/.page-title/#title
          const big = [...document.querySelectorAll('h1,h2,h3,h4,.title,.page-title,#title')]
                      .sort((a,b)=>parseFloat(getComputedStyle(b).fontSize)-parseFloat(getComputedStyle(a).fontSize))[0];
          // Also sample first visible SVG text node, if any (for SVG-rendered titles)
          const svgText = document.querySelector('svg text');
          return [snap(big), snap(svgText)];
        """)
        print("[Title debug]", info)

        # Print options
        print_options = {
            'landscape': False,
            'printBackground': True,
            'preferCSSPageSize': False,  # specifying explicit size below
            'paperWidth': 8.5,
            'paperHeight': 11,
            'marginTop': 0.5,
            'marginBottom': 0.5,
            'marginLeft': 0.75,
            'marginRight': 0.75,
            'scale': 1.0
        }

        result = driver.execute_cdp_cmd('Page.printToPDF', print_options)
        with open(output_pdf, 'wb') as f:
            f.write(base64.b64decode(result['data']))
        print(f"[OK] Wrote PDF → {output_pdf}")

    finally:
        driver.quit()


# Regex to detect plain numbers (int/decimal, optional sign, allows ".5")
NUM_RE = re.compile(r"""
    ^[+-]?(
        (?:\d+(?:\.\d*)?)   # 3, 3., 3.14
        |
        (?:\.\d+)           # .5
    )$
""", re.X)

MATH_SEG_RE = re.compile(
    r'(\\\((?:\\.|[^\\])*?\\\)'        # \( ... \)
    r'|\\\[(?:\\.|[^\\])*?\\\]'        # \[ ... \]
    r'|(?<!\\)\$\$(?:\\.|[^\\])*?\$\$' # $$ ... $$
    r'|(?<!\\)\$(?:\\.|[^\\])*?\$)'    # $ ... $
)

# ========== 2) Number pattern builder ==========
def _make_number_re(allow_percent=False):
    """
    Matches:
      123, -123.45, 1,234, 1,234.56, 12,345,678.9
    (commas must be correct)
    Optionally captures trailing % as group(2) if allow_percent=True.
    """
    grouped = r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?'
    if allow_percent:
        percent = r'(%)?'      # group(2) will be '%' if present
        tail_block = r'(?!\w)' # allow %; we'll include it
    else:
        percent = r''
        tail_block = r'(?![\w%])'  # block % so 50% is not matched

    return re.compile(
        rf'(?<![\w&])'           # not after word char or '&' (entity start)
        rf'(?<![\^_/])'          # avoid x^2, a_1, and immediately after '/'
        rf'(-?{grouped})'        # group(1): the number
        rf'{percent}'            # group(2): optional '%'
        rf'(?![/:]\d)'           # skip 3/4 or 3:15 patterns
        rf'{tail_block}'
    )

# Pre-built default (no percent)
NUMBER_RE = _make_number_re(allow_percent=False)

# ========== 3) Remove XML/DOCTYPE preambles that appeared as text ==========
def _strip_xml_preamble_strings(soup: BeautifulSoup) -> None:
    """
    Remove text nodes that look like XML/DOCTYPE preambles:
      '<?xml ...?>', escaped '&lt;?xml ...&gt;', or mangled 'xml version="..."'
      and '<!DOCTYPE ...>' variants.
    """
    def looks_like_preamble(s: str) -> bool:
        t = s.strip().lower()
        return t.startswith(('<?xml', '&lt;?xml', 'xml version', '<!doctype', '&lt;!doctype'))

    for node in list(soup.find_all(string=True)):
        if looks_like_preamble(str(node)):
            node.extract()

# ========== 4) Main function ==========
def wrap_plain_numbers_in_text(html, allow_percent = False):
   
    if html is None:
        return None

    soup = BeautifulSoup(str(html), 'html.parser')

    for bad in soup.find_all(['script', 'noscript', 'iframe', 'object', 'embed']):
        bad.decompose()

    # Strip XML/DOCTYPE preambles that slipped in as text nodes
    _strip_xml_preamble_strings(soup)

    skip_tags = {'script', 'style', 'svg', 'math', 'code', 'pre'}
    number_re = NUMBER_RE if not allow_percent else _make_number_re(True)

    for node in soup.find_all(string=True):
        if isinstance(node, Comment):
            continue
        parent = node.parent
        if parent and parent.name in skip_tags:
            continue

        text = str(node)
        if not any(ch.isdigit() for ch in text):
            continue

        # 1) Mask existing math so we don't modify inside it
        placeholders = []
        def _mask(m):
            placeholders.append(m.group(0))
            return f'__MATHSEG_{len(placeholders)-1}__'
        masked = MATH_SEG_RE.sub(_mask, text)

        # 2) Replace numbers
        def _wrap(m):
            num = m.group(1)
            pct = m.group(2) if (allow_percent and m.lastindex and m.lastindex >= 2) else None
            return rf'\({num}\%\)' if pct else rf'\({num}\)'
        replaced = number_re.sub(_wrap, masked)

        # 3) Unmask
        def _unmask(m):
            return placeholders[int(m.group(1))]
        unmasked = re.sub(r'__MATHSEG_(\d+)__', _unmask, replaced)

        if unmasked != text:
            node.replace_with(NavigableString(unmasked))

    # Final sweep for any newly-surfaced preamble text
    _strip_xml_preamble_strings(soup)

    return str(soup)

def strip_markup(s):
    """Remove HTML tags, unescape entities, strip whitespace."""
    if s is None:
        return ""
    s = str(s)
    s = re.sub(r"<[^>]+>", "", s)   # strip HTML tags
    s = unescape(s)
    return s.strip()


def fix_the_number(val):
    """If val is just a number, wrap with \( ... \), else return unchanged."""
    if val is None:
        return val
    raw = str(val).strip()
    cleaned = strip_markup(raw)
    
    # avoid double-wrapping if already in math delimiters
    if (cleaned.startswith(r"\(") and cleaned.endswith(r"\)")) or \
       (cleaned.startswith("$") and cleaned.endswith("$")):
        return raw
    
    if NUM_RE.match(cleaned):
        return rf"\({cleaned}\)"
    return raw

def clean_errant_tags(target):
    
    choiceList = ['choice_a','choice_b','choice_c','choice_d']
    
    for choice in choiceList:
        target[choice] = [val.replace("\[","\(") if "\[" in str(val) else val for val in target[choice]]
        target[choice] = [
            str(val).replace("<p>","").replace("</p>","") 
            if "<p>" in str(val) and "</p>" in str(val)
            else val 
            for val in target[choice]
         ]
    
    return target

def create_ex_pset(all_math, subtopic,file_prefix, title_dict):
  
  target_df = all_math[all_math['module_name'] == subtopic].sort_values(by='sort_order')
  
  jaxCols = ['body','prompt','stem','stimulus','choice_a','choice_b','choice_c','choice_d','rationale']
  answers = ['choice_a','choice_b','choice_c','choice_d']
  
  for col in list(set(list(target_df.columns))):
    if col in jaxCols:
      target_df[col] = [clean_mathJax(val) if clean_mathJax(val) else "" for val in target_df[col]]
  
  target_df = clean_errant_tags(target_df)
  
  for col in answers:
    target_df[col] = target_df[col].apply(fix_the_number)
  
  target_df = make_svg_dict(target_df)
  
  for _, row in target_df.iterrows():
    if row['svg_loc'] == 'PROMPT':
      target_df['body'] = target_df['body'].apply(wrap_plain_numbers_in_text)
      target_df['stem'] = target_df['stem'].apply(wrap_plain_numbers_in_text)
      target_df['stimulus'] = target_df['stimulus'].apply(wrap_plain_numbers_in_text)
    elif row['svg_loc'] == 'BODY':
      target_df['body'] = target_df['prompt'].apply(wrap_plain_numbers_in_text)
      target_df['stem'] = target_df['stem'].apply(wrap_plain_numbers_in_text)
      target_df['stimulus'] = target_df['stimulus'].apply(wrap_plain_numbers_in_text)
    elif row['svg_loc'] == 'STEM':
      target_df['body'] = target_df['body'].apply(wrap_plain_numbers_in_text)
      target_df['stem'] = target_df['prompt'].apply(wrap_plain_numbers_in_text)
      target_df['stimulus'] = target_df['stimulus'].apply(wrap_plain_numbers_in_text)
    elif row['svg_loc'] == 'STIMULUS':
      target_df['body'] = target_df['body'].apply(wrap_plain_numbers_in_text)
      target_df['stem'] = target_df['stem'].apply(wrap_plain_numbers_in_text)
      target_df['stimulus'] = target_df['prompt'].apply(wrap_plain_numbers_in_text)
    else:
      target_df['prompt'] = target_df['prompt'].apply(wrap_plain_numbers_in_text)
      target_df['body'] = target_df['body'].apply(wrap_plain_numbers_in_text)
      target_df['stem'] = target_df['stem'].apply(wrap_plain_numbers_in_text)
      target_df['stimulus'] = target_df['stimulus'].apply(wrap_plain_numbers_in_text)
    
    target_df["sort_order"] = [int(val) for val in target_df['sort_order']]
  
  target_df.to_csv(f'{file_prefix}.csv')
  clustered_attempt2(f'{file_prefix}.csv',f"{file_prefix}.html", title_dict[subtopic])
  html_to_pdf_math_enhanced(f'{file_prefix}.html',f'{file_prefix}.pdf')
  
def create_diagnostics(all_math, subtopic,file_prefix, title_dict):
  target_df = all_math[all_math['module_name'] == subtopic].sort_values(by='sort_order')
  
  jaxCols = ['body','prompt','stem','stimulus','choice_a','choice_b','choice_c','choice_d','rationale']
  answers = ['choice_a','choice_b','choice_c','choice_d']
  
  for col in list(set(list(target_df.columns))):
    if col in jaxCols:
      target_df[col] = [clean_mathJax(val) if clean_mathJax(val) else "" for val in target_df[col]]
  
  target_df = clean_errant_tags(target_df)
  
  for col in answers:
    target_df[col] = target_df[col].apply(fix_the_number)
  
  target_df = make_svg_dict(target_df)
  
  for _, row in target_df.iterrows():
    if row['svg_loc'] == 'PROMPT':
      target_df['body'] = target_df['body'].apply(wrap_plain_numbers_in_text)
      target_df['stem'] = target_df['stem'].apply(wrap_plain_numbers_in_text)
      target_df['stimulus'] = target_df['stimulus'].apply(wrap_plain_numbers_in_text)
    elif row['svg_loc'] == 'BODY':
      target_df['body'] = target_df['prompt'].apply(wrap_plain_numbers_in_text)
      target_df['stem'] = target_df['stem'].apply(wrap_plain_numbers_in_text)
      target_df['stimulus'] = target_df['stimulus'].apply(wrap_plain_numbers_in_text)
    elif row['svg_loc'] == 'STEM':
      target_df['body'] = target_df['body'].apply(wrap_plain_numbers_in_text)
      target_df['stem'] = target_df['prompt'].apply(wrap_plain_numbers_in_text)
      target_df['stimulus'] = target_df['stimulus'].apply(wrap_plain_numbers_in_text)
    elif row['svg_loc'] == 'STIMULUS':
      target_df['body'] = target_df['body'].apply(wrap_plain_numbers_in_text)
      target_df['stem'] = target_df['stem'].apply(wrap_plain_numbers_in_text)
      target_df['stimulus'] = target_df['prompt'].apply(wrap_plain_numbers_in_text)
    else:
      target_df['prompt'] = target_df['prompt'].apply(wrap_plain_numbers_in_text)
      target_df['body'] = target_df['body'].apply(wrap_plain_numbers_in_text)
      target_df['stem'] = target_df['stem'].apply(wrap_plain_numbers_in_text)
      target_df['stimulus'] = target_df['stimulus'].apply(wrap_plain_numbers_in_text)
    
    target_df["sort_order"] = [int(val) for val in target_df['sort_order']]
  target_df.to_csv(f'{file_prefix}.csv')
  refined_math(f'{file_prefix}.csv',f"{file_prefix}.html", title_dict[subtopic])
  html_to_pdf_math_enhanced(f'{file_prefix}.html',f'{file_prefix}.pdf')

def ex_pset_diag_flow(item_list, all_math, title_dict):
  for val in item_list:
    if val in diag_sheets:
      create_diagnostics(all_math, val, val, title_dict)
    else:
      create_ex_pset(all_math, val, val, title_dict)
      




def preliminary_cleaning(target): 
    
    jaxCols = ['body','prompt','stem','stimulus','choice_a','choice_b','choice_c','choice_d','rationale']
    answer_choices = ['choice_a','choice_b','choice_c','choice_d']
       
    for col in list(set(list(target.columns))):
        if col in jaxCols:
            target[col] = [clean_mathJax(val) if clean_mathJax(val) else "" for val in target[col]]
    
    target = clean_errant_tags(target)
    
    for choice in answer_choices:
        target[choice] = [wrap_basic_numbers(val) if contains_big_numbers(val) else 
                          wrap_basic_numbers(val) if contains_percent(val) else 
                          wrap_dollar_amounts(val) if contains_dollar_amount(val) else 
                          fix_the_number(val) for val in target[choice]]
    
    return target
  
def clean_question_info(df, colsList):
    for col in colsList:
        df[col] = [
            wrap_basic_numbers(val) if contains_big_numbers(val)
            else wrap_basic_numbers(val) if contains_percent(val)
            else wrap_dollar_amounts(val) if contains_dollar_amount(val)
            else fix_the_number(val)
            for val in df[col]
        ]
    return df


def qcol_clean(target):
    
    qs_dict = {
        "svg_in_prompt" : ['body','stem','stimulus'], 
        "svg_in_body" : ['prompt','stem','stimulus'],
        "svg_in_stem" : ['body','prompt','stimulus'],
        "svg_in_stim" : ['body','stem','prompt'],
        "clean" : ['body','prompt','stem','stimulus']
        }
    
    svg_in_prompt = target[target['svg_loc'] == 'PROMPT']
    svg_in_body = target[target['svg_loc'] == 'BODY']
    svg_in_stem = target[target['svg_loc'] == 'STEM']
    svg_in_stim = target[target['svg_loc'] == 'STIMULUS']
    clean = target[target['svg_loc'] == 'CLEAN']
    
    svg_df_list = [svg_in_prompt, svg_in_body, svg_in_stem, svg_in_stim, clean]
    
    for i in range(len(list(qs_dict.keys()))):
        svg_df_list[i] = clean_question_info(svg_df_list[i], qs_dict[list(qs_dict.keys())[i]])
    
    return svg_df_list


def merge_sort_deploy(df_list, title_dict, mod, subject, sideBySide=True):
    
    output_df = pd.concat(df_list).sort_values(by='sort_order')
    
    output_df.to_csv(f'{subject}_CSV/{mod}.csv')
    
    if sideBySide:
        clustered_attempt2(f'{subject}_CSV/{mod}.csv',f'{subject}_EXHTML/{mod}.html',title_dict[mod])
    else:
        refined_math(f'{subject}_CSV/{mod}.csv',f'{subject}_EXHTML/{mod}.html',title_dict[mod])
    
    html_to_pdf_math_enhanced(f'{subject}_EXHTML/{mod}.html',f'{subject}_exPset/{mod}.pdf')
    
    
def exercisesAndPracticeSets(all_math, title_dict, subject):
  
    warnings.filterwarnings('ignore', 'SettingWithCopyWarning')
    
    display_counter = 0
    
    for module in title_dict.keys():
        
        target = all_math[all_math['module_name'] == module]
        
        target = preliminary_cleaning(target)
        
        target = make_svg_dict(target)
        
        splintered = qcol_clean(target)
        
        if module in diag_sheets:
            merge_sort_deploy(splintered, title_dict, module, subject, sideBySide=False)
        else:
            merge_sort_deploy(splintered, title_dict, module, subject, sideBySide=True)
        
        display_counter += 1
        
        print(f'Module {display_counter} of {len(list(title_dict.keys()))} : {module}')
        
def merge_pdfs(pdf_files, output_name):
	
  pdf_merger = pikepdf.Pdf.new()

  for pdf_file in pdf_files:
    with pikepdf.open(pdf_file) as pdf:
      pdf_merger.pages.extend(pdf.pages)

  pdf_merger.save(f'{output_name}.pdf')


  print(f"Merged PDF saved as {f'{output_name}.pdf'}.")
            