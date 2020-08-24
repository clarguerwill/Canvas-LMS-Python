import time as t
import requests
import pyodbc
import os
import sqlalchemy as db
import smtplib

from sqlalchemy import func
from sqlalchemy.orm import sessionmaker
from datetime import datetime


# Setting Variables ------------------------------------------------------------------------------

THRESHOLD_DATE = 'YYYY-MM-DD'

RECIPIENTS = [
			 {
			  'address' : 'email@email.com', 
			  'subject' : 'Desired Subject Line',
			  'message' : 'Something went wrong'
			  }
			  ,
			 {
			  'address' : 'email2@email.com', 
			  'subject' : 'Desired Subject line',
			  'message' : 'Something went wrong'
			  }
			 ]

DATABASE_NAME = 'Name of the Schools database in EK12'

MAIN_URL = 'URL to access the schools API. EX: https://schoolname.instructure.com/api/v1'

CANVAS_PASSWORD_FILE_NAME = 'name of the text file that contains the canvas information'




# Functions ------------------------------------------------------------------------------------------------
def send_email(error='', table='', logfile=''):

	dt = datetime.now()
	sender_email = os.getenv('EMAIL_ADDRESS')
	password = os.getenv('EMAIL_PASSWORD')
	smtpObj = smtplib.SMTP('smtp-mail.outlook.com', 587)
	smtpObj.starttls()
	smtpObj.login(sender_email, password)

	for person in RECIPIENTS:

		if table and error:
			msg = '''Subject: {}\n\n
					 {}\n One or both of these two errors may have occured.\n
					 There was an error loading this table: 
					 {}\n
					 Python returned this error message:\n
					 {}\n
					 The time of occurance was: {}'''.format(person['subject'], person['message'], table, error, dt)
		elif table:
			msg = '''Subject: {}\n\n
					 {}\n
					 There was an error loading this table: 
					 {}\n
					 The time of occurance was: {}'''.format(person['subject'], person['message'], table, dt)
		
		elif error:
			msg = '''Subject: {}\n\n
					 {}\n
					 Python returned this error message:\n
					 {}\n
					 The time of occurance was: {}'''.format(person['subject'], person['message'], error, dt)

		else:
			msg = '''Subject: {}\n\n
					 {}\n
					 The data for these request returned an error:\n
					 {}'''.format(person['subject'], person['message'], logfile)

		smtpObj.sendmail(sender_email, person['address'], msg)
	
	smtpObj.quit()


def get_access_token():
	file = open(CANVAS_PASSWORD_FILE_NAME, 'r')
	passwords = eval(str(file.read()))
	file.close()
	client_id = passwords.get('client_id')
	client_secret = passwords.get('client_secret')
	token_url = passwords.get('token_url')
	refresh_token = passwords.get('refresh_token')

	params = {'grant_type':'refresh_token', 'refresh_token': refresh_token}
	r = requests.post(token_url, auth=(client_id, client_secret), data=params)

	token = r.json().get('access_token')[5:]
	headers = {'Authorization': 'Bearer {}'.format(token)}
	return headers


def log_this(request_error):
	with open(ERROR_LOG_FILENAME, 'a+') as f:
		f.write('{}:    {}\n'.format(datetime.now().time(), request_error))
	f.close


def get_all_results(url, headers, params={}, extra=''):
	r = requests.get('{}{}?per_page=100{}'.format(MAIN_URL, url, extra), headers=headers, data=params)		
	if r.status_code == 200:
		values_list = r.json()
		while 'next' in r.links:
			r = requests.get(r.links['next']['url'], headers=headers, data=params)
			values_list.extend(r.json())
		return values_list
	elif r.status_code != 404:
		request_error = '{} - {}'.format(r.url, r.status_code)
		print(request_error)
		log_this(request_error)
		return None
	else:
		return None


def start_connection_with_EK12():
	user = os.getenv('EK12_USERNAME')
	passw = os.getenv('EK12_PASSWORD')
	host = os.getenv('EK12_HOST')
	port = os.getenv('EK12_PORT')

	# Connect to the EK12 Database
	engine = db.create_engine('mssql+pyodbc://{}:{}@{}:{}/{}?driver=ODBC+Driver+17+for+SQL+Server'.format(user, passw, host, port, DATABASE_NAME))
	connection = engine.connect()
	metadata = db.MetaData()
	Session = sessionmaker(bind=engine)
	session = Session()
	return connection, engine, metadata, session


def declare_database_table(tablename):
	t = db.Table(tablename, METADATA, autoload=True, autoload_with=ENGINE)
	return t


def delete_this_table_data(tablename):
	CONNECTION.execution_options(autocommit=True).execute("""TRUNCATE TABLE {}""".format(tablename))


def insert_data_into_database(tablename, data, t):
	CONNECTION.execute(t.insert(), data)


def get_students(headers):
	url = '/accounts/1/users'
	params = {'enrollment_type' : 'student'}
	response = get_all_results(url, headers, params=params)

	if response:
		delete_this_table_data('Canvas_Students')
		t = declare_database_table('Canvas_Students')

		for item in response:
			row_of_data = {'id' : item['id'],
						'name' : item['name'],
						'sis_user_id' : item['sis_user_id'],
						'sis_import_id' : item['sis_import_id'],
						'login_id' : item['login_id'],
						'sortable_name' : item['sortable_name'],
						'created_at' : item['created_at']
						}
			insert_data_into_database('Canvas_Students', row_of_data, t)


def get_sub_accounts(headers):
	url = '/accounts/1/sub_accounts'
	response = get_all_results(url, headers)
	sub_accounts = []

	if response:
		delete_this_table_data('Canvas_SubAccounts')
		t = declare_database_table('Canvas_SubAccounts')

		for item in response:
			sub_accounts.append({'id': item['id'],
							'name': item['name'],
							'sis_account_id': item['sis_account_id'],
							'sis_import_id': item['sis_import_id'],
							'workflow_state': item['workflow_state']
							})

		insert_data_into_database('Canvas_SubAccounts', sub_accounts, t)
	
	return sub_accounts


def get_courses(headers):
	courses = []

	for sub_account in SUB_ACCOUNTS:
		url = '/accounts/{}/courses'.format(sub_account['id'])
		extra = '&include[]=term&include[]=total_students'
		response = get_all_results(url, headers, extra=extra)
		
		if response:
			t = declare_database_table('Canvas_Courses')

			for item in response:
				courses.append({'id': item['id'],
							'name': item['name'],
							'course_code': item['course_code'],
							'total_students': item['total_students'],
							'sis_course_id': item['sis_course_id'],
							'sis_import_id': item['sis_import_id'],
							'account_id': item['account_id'],
							'created_at': item['created_at'],
							'term_id': item['term']['id'],
							'term_start': item['term']['start_at'],
							'term_end': item['term']['end_at'],
							'term_sis_id': item['term']['sis_term_id'],
							'term_sis_import_id': item['term']['sis_import_id']
							})
	if len(courses) > 0:
		delete_this_table_data('Canvas_Courses')
		insert_data_into_database('Canvas_Courses', courses, t)

	return courses


def get_active_courses_and_sections(headers):
	active_courses = []
	active_sections = []

	for sub_account in SUB_ACCOUNTS:
		url = '/accounts/{}/courses'.format(sub_account['id'])
		extra = '&include[]=term&include[]=total_students'
		params = {'enrollment_state' : 'active'}
		a_courses = get_all_results(url, headers, extra=extra, params=params)

		if a_courses:
			for course in a_courses:
				active_courses.append(course['id'])
				url = '/courses/{}/sections'.format(course['id'])
				a_sections = get_all_results(url, headers)

				if a_sections:
					for section in a_sections:
						active_sections.append((section['id'], course['id']))

	return active_courses, active_sections


def get_sections(headers):
	table_of_data = []

	for course in ALL_COURSES:
		url = '/courses/{}/sections'.format(course['id'])
		extra = '&include[]=total_students'
		response = get_all_results(url, headers, extra=extra)

		if response:
			t = declare_database_table('Canvas_Sections')

			for item in response:
				table_of_data.append({'id': item['id'],
							'course_id': item['course_id'],
							'name': item['name'],
							'sis_section_id': item['sis_section_id'],
							'integration_id': item['integration_id'],
							'sis_course_id': item['sis_course_id'],
							'sis_import_id': item['sis_import_id'],
							'start_at': item['start_at'],
							'end_at': item['end_at'],
							'total_students': item['total_students']
							})

	if len(table_of_data) > 0:
		delete_this_table_data('Canvas_Sections')
		insert_data_into_database('Canvas_Sections', table_of_data, t)



def get_submissions(headers):
	t = declare_database_table('Canvas_Submissions')

	for section in ACTIVE_SECTIONS:
		extra = '&student_ids=all&enrollment_state=active'
		params = {'submitted_since' : THRESHOLD_DATE + 'T00:00:00Z'}
		url = '/sections/{}/students/submissions'.format(section[0])
		response = get_all_results(url, headers, extra=extra, params=params)

		if response:		
			table_of_data = []	
			
			for item in response:
				table_of_data.append({'id': item['id'],
									'user_id': item['user_id'],
									'course_id' : section[1],
									'section_id' : section[0],
									'assignment_id': item['assignment_id'],
									'entered_grade': item['entered_grade'],
									'entered_score': item['entered_score'],
									'submission_type': item['submission_type'],
									'workflow_state': item['workflow_state'],
									'late': item['late'],
									'submitted_at': item['submitted_at']
									})
			
			if len(table_of_data) > 0:
				insert_data_into_database('Canvas_Submissions', table_of_data, t)


def get_page_views(headers):
	params = {'enrollment_state' : 'active'}
	page_views = []
	t = declare_database_table('Canvas_PageViews')

	for course in ACTIVE_COURSES:
		params = {'enrollment_state' : 'active', 'enrollment_type' : 'student'}
		url = '/courses/{}/users'.format(course)
		headers = get_access_token()
		response = get_all_results(url, headers, params=params)
		
		if response:
			table_of_data = []
			course_users = response

			for user in course_users:
				url = '/courses/{}/analytics/users/{}/activity'.format(course, user['id'])
				response = get_all_results(url, headers)

				if response:
					for key, value in response['page_views'].items():
						if datetime.strptime(key[:10], '%Y-%m-%d') >= datetime.strptime(THRESHOLD_DATE, '%Y-%m-%d'):
							table_of_data.append({'course_id': course,
												'user_id': user['id'],
												'datetime': key.replace('T', ' ').strip()[:-6],
												'page_views': value
												})
			
			if len(table_of_data) > 0:
				insert_data_into_database('Canvas_PageViews', table_of_data, t)


# Main Program ------------------------------------------------------------------------------------------
start = t.time()

try:
	ERROR_LOG_FILENAME = "ErrorLog {}.txt".format(str(datetime.now()).strip().replace(':', '_'))

	CONNECTION, ENGINE, METADATA, SESSION = start_connection_with_EK12()
	delete_this_table_data('Canvas_Submissions')
	delete_this_table_data('Canvas_PageViews')

	headers = get_access_token()

	print('Starting SubAccounts')
	SUB_ACCOUNTS = get_sub_accounts(headers)

	print('Starting Students')
	get_students(headers)

	print('Starting Courses')
	ALL_COURSES = get_courses(headers)

	headers = get_access_token()

	print('Starting Sections')
	get_sections(headers)

	headers = get_access_token()

	print('Starting Active Data')
	ACTIVE_COURSES, ACTIVE_SECTIONS = get_active_courses_and_sections(headers)

except Exception as error_message:
	send_email(error=error_message, table = 'Sub Accounts')


try:
	headers = get_access_token()
	print('Starting Submissions')
	get_submissions(headers)

except Exception as error_message:
	send_email(error=error_message, table='Canvas_Submissions')


try:
	headers = get_access_token()
	print('Starting PageViews')
	get_page_views(headers)

except Exception as error_message:
	send_email(error=error_message, table='Canvas_PageViews')


end = t.time()
print(end - start)


# Code for sending request errors
if os.path.exists(ERROR_LOG_FILENAME):
	with open(ERROR_LOG_FILENAME,'r') as f:
		request_errors = f.readlines()
	f.close()
	request_errors = ''.join(request_errors)
	send_email(logfile=request_errors)




