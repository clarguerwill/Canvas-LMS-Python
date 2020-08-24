from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy import *
import os

DATABASE = 'Name of the School in EK12 Database'

# Retrieving Environment Variables
user = os.getenv('DB_USERNAME')
passw = os.getenv('DB_PASSWORD')
host = os.getenv('DB_HOST')
port = os.getenv('DB_PORT')

engine = create_engine('mssql+pyodbc://{}:{}@{}:{}/{}?driver=ODBC+Driver+17+for+SQL+Server'.format(user, passw, host, port, DATABASE))
connection = engine.connect()
metadata = MetaData()
Base = declarative_base()


class CanvasStudents(Base):
	__tablename__ = 'Canvas_Students'
	id = Column(String(200), primary_key = True)
	name = Column(String)
	sis_user_id = Column(String)
	sis_import_id = Column(String)
	login_id = Column(String)
	sortable_name = Column(String)
	created_at = Column(Date)


class SubAccounts(Base):
	__tablename__ = 'Canvas_SubAccounts'
	id = Column(String(200), primary_key=True)
	name = Column(String)
	sis_account_id = Column(String)
	sis_import_id = Column(String)
	workflow_state = Column(String)
	

class CanvasCourses(Base):
	__tablename__ = 'Canvas_Courses'
	id = Column(String(200), primary_key = True)
	name = Column(String)
	course_code = Column(String)
	total_students = Column(String)
	sis_course_id = Column(String)
	sis_import_id = Column(String)
	account_id = Column(String)
	created_at = Column(Date)
	term_id = Column(String) # id
	term_start = Column(Date) # start_at
	term_end = Column(Date) # end_at
	term_sis_id = Column(String) # sis_term_id
	term_sis_import_id = Column(String) # sis_import_id


class CanvasSections(Base):
	__tablename__ = 'Canvas_Sections'
	id = Column(String(200), primary_key = True)
	course_id = Column(String)
	name = Column(String)
	sis_section_id = Column(String)
	integration_id = Column(String)
	sis_import_id = Column(String)
	sis_course_id = Column(String)
	start_at = Column(Date) # start_at
	end_at = Column(Date) # end_at
	total_students = Column(Integer) #include[]=total_students


class CanvasSubmissions(Base):
	__tablename__ = 'Canvas_Submissions'
	id = Column(String(200), primary_key = True)
	user_id = Column(String)
	course_id = Column(String)
	section_id = Column(String)
	assignment_id = Column(String)
	entered_grade = Column(String)
	entered_score = Column(Float)
	submission_type = Column(String)
	workflow_state = Column(String)
	late = Column(String)
	submitted_at = Column(DateTime)
	


class CanvasPageViews(Base):
	__tablename__ = 'Canvas_PageViews'
	datetime = Column(DateTime, primary_key = True)
	course_id = Column(String(200), primary_key = True)
	user_id = Column(String(200), primary_key = True)
	page_views = Column(Integer)


Base.metadata.create_all(engine)


print("Tables Created Successfully!")
