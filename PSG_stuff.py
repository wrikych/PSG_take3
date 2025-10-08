import numpy as np 
import pandas as pd
from sqlalchemy import create_engine, text, bindparam
from urllib.parse import quote_plus
import random 

from transcription_helpers import *

appearances_list = ['902D LOWER', '903D MEDIUM', '1000D LOWER',
       '1000D UPPER', '902D UPPER', '1000D MEDIUM', '903D LOWER',
       '902D MEDIUM', '903D UPPER', '901D UPPER', '904D LOWER', '901D LOWER',
       '904D MEDIUM', '904D UPPER', '901D MEDIUM', 'BB3 UPPER', 'BB5 MEDIUM',
       'BB9 MEDIUM', 'BB10 MEDIUM', 'BB4 MEDIUM', 'BB5 UPPER', 'BB2 UPPER',
       'BB2 LOWER', 'BB9 UPPER', 'BB4 LOWER', 'BB6 MEDIUM', 'BB8 UPPER',
       'BB2 MEDIUM', 'BB10 LOWER', 'BB1 MEDIUM', 'BB1 UPPER', 'BB10 UPPER',
       'BB5 LOWER', 'BB4 UPPER', 'BB7 LOWER', 'BB6 LOWER', 'BB8 MEDIUM',
       'BB3 LOWER', 'BB6 UPPER', 'BB8 LOWER', 'BB7 UPPER', 'BB3 MEDIUM',
       'BB7 MEDIUM', 'BB9 LOWER', 'BB1 LOWER', 'LT9_Module2', 'LT9_Module1',
       'LT10_Module1', 'LT4_Module1', 'LT8_Module1', 'LT3_Module2',
       'LT7_Module1', 'LT6_Module1', 'LT2_Module2', 'LT2_Module1',
       'LT8_Module2', 'LT4_Module2', 'LT3_Module1', 'LT6_Module2',
       'LT10_Module2', 'LT5_Module1', 'LT7_Module2', 'LT1_Module1',
       'LT5_Module2', 'LT1_Module2']


USER = 'portalmycramcrew_ro'
PWD  = quote_plus("Cr@mCrew!123")  # encodes @ -> %40, ! stays fine
HOST = 'mycramcrew.com'
PORT = 3306
DB = 'portalmycramcrew_live'

engine = create_engine(f"mysql+pymysql://{USER}:{PWD}@{HOST}:{PORT}/{DB}?charset=utf8mb4")

def create_student_data(FULL_NAME):
    full_name_param = bindparam('fullName')
    query = text("""
	select distinct first_name, last_name, event_date, module_name, subject, sort_order, primary_class_cd_desc, skill_desc, questionId, difficulty, question_type, student_answer, time_spent_seconds, is_correct_answer
	from user_dsat_practice_test 
	join user 
	on user_dsat_practice_test.fk_student_user_id = user.user_id
	join dsat_practice_test 
	on user_dsat_practice_test.fk_dsat_practice_test_id = dsat_practice_test.dsat_practice_test_id 
	join user_event 
	on user_dsat_practice_test.fk_user_event_id = user_event.user_event_id 
	join user_dsat_practice_test_answer_sheet  
	on user_dsat_practice_test.user_dsat_practice_test_id = user_dsat_practice_test_answer_sheet.fk_user_dsat_practice_test_id 
	join blue_book_question_header 
	on user_dsat_practice_test_answer_sheet.question_uid = blue_book_question_header.uId 
	join dsat_test_module_questions 
	on user_dsat_practice_test_answer_sheet.question_uid = dsat_test_module_questions.fk_bluebook_question_uid 
	join dsat_test_module 
	on dsat_test_module_questions.fk_dsat_test_module_id = dsat_test_module.dsat_test_module_id 
	WHERE CONCAT(first_name, " ", last_name) = :fullName
	""").bindparams(full_name_param)
    
    with engine.connect() as conn:
        student_df = pd.read_sql(query, conn, params={"fullName" : FULL_NAME})
    return student_df

def fix_modules(student):
  mods_dict = {}
  mods_to_delete = []
  for val in list(set(list(student.module_name.unique()))):
    mods_dict[val] = student[student['module_name'] == val].shape[0]
  for mod in mods_dict.keys():
    if 'Math' in mod: 
      if mods_dict[mod] != 22:
        mods_to_delete.append(mod)
      else:
        pass
    elif 'Verbal' in mod:
      if mods_dict[mod] != 27:
        mods_to_delete.append(mod)
      else:
        pass
    else:
      pass
  student = student[~student['module_name'].isin(mods_to_delete)]
  return student

def filter_desired_content(student, subject=None, topic_list=None):
    if subject:
        student = student[student['subject'] == subject]   
    if topic_list: 
        student = student[student['primary_class_cd_desc'].isin(topic_list)]
    return student

def get_importance_index(subset):
  count = np.log1p(subset.shape[0])
  Y = subset[subset['is_correct_answer']=='Y'].shape[0]
  N = subset[subset['is_correct_answer']=='N'].shape[0]
  acc = Y / (Y+N)
  avg_time = subset['time_spent_seconds'].mean()
  avg_diff = subset['difficulty'].mean()
  return (1-acc) * avg_time * count * (4-avg_diff)

def cycle_through_subtopics(main_df):
  resultant_dict = {}
  list_of_subtopics = list(set(list(main_df['skill_desc'])))
  diff_dict = {'E' : 1, 
               'M' : 2,
               'H' : 3}
  main_df['difficulty'] = [diff_dict[val] for val in main_df['difficulty']]
  for val in list_of_subtopics:
    test_subset = main_df[main_df['skill_desc']==val]
    resultant_dict[val] = get_importance_index(test_subset)
  return resultant_dict

def find_dict_sum(subs):
  sum = 0
  for val in subs.keys():
    sum += subs[val]
  return sum

def get_question_amounts(resultant_dict, number_of_questions=30):
  sum = find_dict_sum(resultant_dict)
  sorted_analysis = dict(sorted(resultant_dict.items(), key=lambda item: item[1], reverse=True))
  sorted_analysis = {k: v / sum for k, v in sorted_analysis.items()}
  for val in sorted_analysis:
    sorted_analysis[val] = int(sorted_analysis[val] * number_of_questions)
  return sorted_analysis

def instantiate_pool(subject):
    local_db = pd.read_csv('local_db.csv')
    total_appearances = []
    for _, row in local_db.iterrows():
        total_val = 0  # reset for each row
        for val in appearances_list:
            total_val += row[val]
        total_appearances.append(total_val)
    local_db['total_appearances'] = total_appearances
    available_questions = local_db[local_db['total_appearances'] == 0]
    if subject == 'Math':
        available_questions = available_questions[available_questions['subject'] == 'Math']
    elif subject == 'Verbal':
        available_questions = available_questions[available_questions['subject'] == 'Verbal']
    return available_questions

def get_selected_questions(amounts_dict, pool_df, target_amount=30):
    target_ids = []
    key_list = list(amounts_dict.keys())
    i = 0
    while find_dict_sum(amounts_dict) < target_amount:
        if i < len(key_list):
            target_key = key_list[i]
            amounts_dict[target_key] += 1
        else:
            i -= (len(key_list) // 2)
            target_key = key_list[i]
            amounts_dict[target_key] += 1
    for val in amounts_dict.keys():
        pool = list(set(list(pool_df[pool_df['skill_desc'] == val]['questionId'])))
        size = amounts_dict[val]
        tgt_lst = random.sample(pool, size)
        target_ids += tgt_lst
    return target_ids

def pull_questionDetailsFromDB(target_ids):
    target_ids_param = bindparam("ids", expanding=True)
    query = text("""
        SELECT 
            ROW_NUMBER() OVER (ORDER BY questionId) AS sort_order,
            questionId, 
            prompt, 
            body, 
            stem, 
            stimulus, 
            choice_a, 
            choice_b, 
            choice_c, 
            choice_d, 
            d.correct_choice, 
            rationale
        FROM blue_book_question_header h 
        JOIN blue_book_question_details d 
            ON h.uId = d.uId 
        WHERE fk_dsat_question_usage_type_id < 3
          AND questionId IN :ids
    """).bindparams(target_ids_param)
    with engine.connect() as conn:
        target_questions = pd.read_sql(
            query,
            conn,
            params={"ids": target_ids}
        )
    return target_questions

def generate_practice_set(student_name, desired_subject, desired_question_amount, desired_topics=None):
    student_info = create_student_data(student_name)
    student_info = fix_modules(student_info)
    student_info = filter_desired_content(student_info, subject=desired_subject, topic_list=desired_topics)
    subs_dict = cycle_through_subtopics(student_info)
    q_amounts = get_question_amounts(subs_dict)
    pool_df = instantiate_pool(desired_subject)
    selected_questions = get_selected_questions(q_amounts, pool_df, target_amount=desired_question_amount)
    worksheet_df = pull_questionDetailsFromDB(selected_questions)
    worksheet_df.to_csv('ws_solutions.csv')
    worksheet_df.drop(columns=['correct_choice','rationale']).to_csv('ws_questions.csv')
    refined_math('ws_questions.csv','ws_questions.html',f'{student_name} : {desired_subject} Practice Set')
    html_to_pdf_math_enhanced('ws_questions.html','ws_questions.pdf')
    refined_math('ws_solutions.csv','ws_solutions.html',f'{student_name} : {desired_subject} Practice Set Solutions')
    html_to_pdf_math_enhanced('ws_solutions.html','ws_solutions.pdf')
    merge_pdfs(['ws_questions.pdf','ws_solutions.pdf'], 'generated_practice_set')