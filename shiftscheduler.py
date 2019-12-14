from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, date
from calendar import monthrange, prevmonth, nextmonth
import ibm_db
import os


app=Flask(__name__)
app.secret_key='secret123'
csrf=CSRFProtect(app)


dsn_driver = "{IBM DB2 ODBC DRIVER}"
dsn_database = "BLUDB"          
dsn_hostname = "dashdb-txn-sbox-yp-lon02-02.services.eu-gb.bluemix.net" 
dsn_port = "50000"                
dsn_protocol = "TCPIP"         
dsn_uid = "dtv29943"    
dsn_pwd = "ph1hkr2cxf6c^gzs"      

dsn = (
	"DRIVER={0};"
	"DATABASE={1};"
	"HOSTNAME={2};"
	"PORT={3};"
	"PROTOCOL={4};"
	"UID={5};"
	"PWD={6};").format(dsn_driver, dsn_database, dsn_hostname, dsn_port, dsn_protocol, dsn_uid, dsn_pwd)


@app.route('/', methods=['GET','POST'])
def index():
	# i need session username to welcome user
	# i need all teams from sql db2
	
	conn = ibm_db.connect(dsn, "", "")
	
	teams={}
	sql="select * from teams;"
	selectStmt = ibm_db.exec_immediate(conn, sql)
	dictionary = ibm_db.fetch_assoc(selectStmt)
	while dictionary != False:
		teams.update({dictionary['TEAM_ID']:dictionary['TEAM_NAME']})
		dictionary = ibm_db.fetch_assoc(selectStmt)
	current_month = datetime.now().month
	current_year = datetime.now().year
	return render_template('index.html', teams=teams, month=current_month, year=current_year)

@app.route('/team/<string:team_name>/schedule/<int:month>/<int:year>', methods=['GET'])
def schedule(team_name, month, year):
	#is is team id, so i need first query team tabel and get list of agents
	#i need all team members
	shifts={}
	team_members=[]
	team={}
	month_length=monthrange(year,month)[1]
	#month days is 3 letter string to help out with date example 'Mon'
	month_days=[]
	weekends=[]
	for x in range(1,month_length+1):
		month_days.append(date(year,month,x).strftime('%A')[:3])
		if date(year,month,x).weekday()==5 or  date(year,month,x).weekday()==6:
			weekends.append('WE')
		else:
			weekends.append('BH')
	conn = ibm_db.connect(dsn, "", "")
	sql="select * from %s;" % (team_name)
	selectStmt = ibm_db.exec_immediate(conn, sql)
	dictionary = ibm_db.fetch_assoc(selectStmt)
	while dictionary != False:
		team.update({dictionary['TEAM_MEMBER_ID']:dictionary['FNAME']})
		team_members.append(dictionary['FNAME'])
		dictionary = ibm_db.fetch_assoc(selectStmt)

	for each in team_members:
		shifts.update({each:None})

	for each_member in team_members:
		shift={}
		sql="select shift,month_s,day_s from shifts where agent_s='%s' and month_s=%s and year_s=%s ;" % (each_member,month, year)
		selectStmt = ibm_db.exec_immediate(conn, sql)
		dictionary = ibm_db.fetch_assoc(selectStmt)
		while dictionary != False:
			shift.update({dictionary['DAY_S']:dictionary['SHIFT']})
			dictionary = ibm_db.fetch_assoc(selectStmt)
		shifts.update({each_member:shift})
		
	month_name=date(year,month,1).strftime('%B')
	year_name=date(year,month,1).strftime('%Y')
	
	ibm_db.close(conn)
	return render_template('schedule_table.html', month=month, year=year, month_name=month_name, year_name=year_name, weekends=weekends, month_length=month_length, shifts=shifts, team_members=team_members, team_name=team_name, month_days=month_days)

@app.route('/team/<string:team_name>/edit/schedule/<int:month>/<int:year>',methods=['GET','POST'])
def edit_schedule(team_name, month, year):
	#i am fetching shifts to prepopulate form
	shifts={}
	team_members=[]
	team={}
	month_days=[]
	month_length=monthrange(year,month)[1]
	weekends=[]
	for x in range(1,month_length+1):
		month_days.append(date(year,month,x).strftime('%A')[:3])
		if date(year,month,x).weekday()==5 or  date(year,month,x).weekday()==6:
			weekends.append('WE')
		else:
			weekends.append('BH')
	
	try:
		conn = ibm_db.connect(dsn, "", "")
		
	except:
		print ("Unable to connect to database")
	sql="select * from %s;" % (team_name)
	selectStmt = ibm_db.exec_immediate(conn, sql)
	dictionary = ibm_db.fetch_assoc(selectStmt)
	while dictionary != False:
		team.update({dictionary['TEAM_MEMBER_ID']:dictionary['FNAME']})
		team_members.append(dictionary['FNAME'])
		dictionary = ibm_db.fetch_assoc(selectStmt)

	for each in team_members:
		shifts.update({each:None})
	
	for each_member in team_members:
		shift={}
		sql="select shift,month_s,day_s from shifts where agent_s='%s' and month_s=%s and year_s=%s ;" % (each_member,month, year)
		selectStmt = ibm_db.exec_immediate(conn, sql)
		dictionary = ibm_db.fetch_assoc(selectStmt)
		while dictionary != False:
			shift.update({dictionary['DAY_S']:dictionary['SHIFT']})
			dictionary = ibm_db.fetch_assoc(selectStmt)
		shifts.update({each_member:shift})
		
	month_name=date(year,month,1).strftime('%B')
	year_name=date(year,month,1).strftime('%Y')
	
	ibm_db.close(conn)
	

	if request.method=='POST':
		result=request.form.to_dict()
		
		try:
			conn = ibm_db.connect(dsn, "", "")
		except:
			print ("Unable to connect to database")
		
		for each in team_members:
			for x in range(1,month_length+1):
				y= each+str(x)
				
				sql="""MERGE INTO SHIFTS
					USING ( VALUES (%s, %s, %s, '%s', '09:00','17:00','%s') ) AS SOURCE(YEAR_S, MONTH_S, DAY_S, SHIFT, START_S, END_S , AGENT_S)
					ON SHIFTS.YEAR_S=SOURCE.YEAR_S AND SHIFTS.MONTH_S=SOURCE.MONTH_S AND SHIFTS.DAY_S=SOURCE.DAY_S AND SHIFTS.START_S=SOURCE.START_S AND SHIFTS.END_S=SOURCE.END_S AND SHIFTS.AGENT_S=SOURCE.AGENT_S
					WHEN MATCHED THEN UPDATE 
					SET SHIFT=SOURCE.SHIFT
					WHEN NOT MATCHED THEN INSERT VALUES (SOURCE.YEAR_S, SOURCE.MONTH_S, SOURCE.DAY_S, SOURCE.SHIFT,SOURCE.START_S,SOURCE.END_S, SOURCE.AGENT_S);
					""" % (year, month, x, result[y] ,each )	
				stmt=ibm_db.exec_immediate(conn, sql)
		ibm_db.close(conn)
		flash('Database updated', "success")
		return redirect(url_for('schedule',team_name=team_name, month=month, year=year))
	return render_template('edit_schedule_table.html', month=month, year=year, month_name=month_name, year_name=year_name, weekends=weekends,month_length=month_length, shifts=shifts, team_members=team_members, team_name=team_name, month_days=month_days)

@app.route('/next_month/<string:team_name>/<int:month>/<int:year>', methods=['GET'])
def next_month(team_name, month, year):
	variable=nextmonth(year,month)
	year=variable[0]
	team_name=team_name
	month=variable[1]
	return redirect(url_for('schedule', team_name=team_name, month=month, year=year, ))

@app.route('/prev_month/<string:team_name>/<int:month>/<int:year>', methods=['GET'])
def prev_month(team_name, month, year):
	variable=prevmonth(year,month)
	year=variable[0]
	team_name=team_name
	month=variable[1]
	return redirect(url_for('schedule', team_name=team_name, month=month, year=year ))

@app.route('/today_month/<string:team_name>/<int:month>/<int:year>', methods=['GET'])
def today_month(team_name, month, year):
	current_month = datetime.now().month
	current_year = datetime.now().year
	team_name=team_name
	return redirect(url_for('schedule', team_name=team_name, month=current_month, year=current_year ))

#################################

@app.route('/next_month_edit/<string:team_name>/<int:month>/<int:year>', methods=['GET'])
def next_month_edit(team_name, month, year):
	variable=nextmonth(year,month)
	year=variable[0]
	team_name=team_name
	month=variable[1]
	return redirect(url_for('edit_schedule', team_name=team_name, month=month, year=year, ))

@app.route('/prev_month_edit/<string:team_name>/<int:month>/<int:year>', methods=['GET'])
def prev_month_edit(team_name, month, year):
	variable=prevmonth(year,month)
	year=variable[0]
	team_name=team_name
	month=variable[1]
	return redirect(url_for('edit_schedule', team_name=team_name, month=month, year=year ))

@app.route('/today_month_edit/<string:team_name>/<int:month>/<int:year>', methods=['GET'])
def today_month_edit(team_name, month, year):
	current_month = datetime.now().month
	current_year = datetime.now().year
	team_name=team_name
	return redirect(url_for('edit_schedule', team_name=team_name, month=current_month, year=current_year ))

#######################################

@app.route('/administration')
def administration():
	try:
		conn = ibm_db.connect(dsn, "", "")
	except:
		print ("Unable to connect to database")
	teams={}
	sql="select * from teams;"
	selectStmt = ibm_db.exec_immediate(conn, sql)
	dictionary = ibm_db.fetch_assoc(selectStmt)
	while dictionary != False:
		teams.update({dictionary['TEAM_ID']:dictionary['TEAM_NAME']})
		dictionary = ibm_db.fetch_assoc(selectStmt)
	ibm_db.close(conn)
	return render_template('administration.html', teams=teams)

class NewTeamForm(Form):
	title =StringField('Title', [validators.Length(min=1, max=100)])

@app.route('/administration/create_new_team',methods=['GET','POST'])
def create_new_team():
	form=NewTeamForm(request.form)
	if request.method=='POST' and form.validate():
		title = form.title.data
		try:
			conn = ibm_db.connect(dsn, "", "")
		except:
			print ("Unable to connect to database")

		sql="""CREATE TABLE %s (
		TEAM_MEMBER_ID integer not null GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1)
		,FNAME VARCHAR(100)
		);""" % (title)
		CreateStmt = ibm_db.exec_immediate(conn, sql)

		sql="""INSERT INTO teams (team_name) VALUES
		'%s';
		"""% (title)
		InsertStmt = ibm_db.exec_immediate(conn, sql)
		ibm_db.close(conn)
		flash('New team has been created', "success")
		return redirect(url_for('administration'))
	return render_template('create_new_team.html', form=form)

@app.route('/administration/team/<string:team_name>/edit', methods=['GET','POST'])
def edit_team(team_name):
	team_members=[]
	try:
		conn = ibm_db.connect(dsn, "", "")
	except:
		print ("Unable to connect to database")
	sql="select * from %s;" % (team_name)
	selectStmt = ibm_db.exec_immediate(conn, sql)
	dictionary = ibm_db.fetch_assoc(selectStmt)
	while dictionary != False:
		team_members.append(dictionary['FNAME'])
		dictionary = ibm_db.fetch_assoc(selectStmt)
	ibm_db.close(conn)
	return render_template('edit_team.html', team_name=team_name, team_members=team_members)

@app.route('/delete_team_member/<string:team_name>/<string:member>',methods=['POST'])
def delete_team_member(team_name,member):
	try:
		conn = ibm_db.connect(dsn, "", "")
	except:
		print ("Unable to connect to database")
	sql="""DELETE FROM %s
	WHERE FNAME='%s';
	""" % (team_name, member)
	deleteStmt = ibm_db.exec_immediate(conn, sql)
	flash('Member deleted', "success")
	ibm_db.close(conn)
	return redirect(url_for('edit_team', team_name=team_name))

@app.route('/delete_team/<string:team_name>', methods=['POST'])
def delete_team(team_name):
	try:
		conn = ibm_db.connect(dsn, "", "")
	except:
		print ("Unable to connect to database")
	sql="drop table %s" % (team_name)
	deleteStmt = ibm_db.exec_immediate(conn, sql)
	sql="""DELETE FROM TEAMS
	WHERE TEAM_NAME='%s';
	""" % (team_name)
	deleteStmt = ibm_db.exec_immediate(conn, sql)
	ibm_db.close(conn)
	flash('Team deleted', "success")
	return redirect(url_for('administration'))

class NewMemberForm(Form):
	name =StringField('Name', [validators.Length(min=1, max=100)])

@app.route('/administration/add_new_member/<string:team_name>', methods=['GET','POST'])
def add_new_member(team_name):
	form=NewMemberForm(request.form)
	if request.method=='POST' and form.validate():
		name=form.name.data
		try:
			conn = ibm_db.connect(dsn, "", "")
		except:
			print ("Unable to connect to database")

		sql="""INSERT INTO %s (FNAME) VALUES '%s';
		"""% (team_name, name)
		InsertStmt = ibm_db.exec_immediate(conn, sql)
		ibm_db.close(conn)
		flash('New member has been added to the team', "success")
		return redirect(url_for('edit_team', team_name=team_name),code=302)

	return render_template('add_new_member.html', form=form)

#port = os.getenv('PORT', '5000')
#if __name__ == "__main__":
#	app.secret_key='mybestsecretkeyever'
#	app.run(host='0.0.0.0', port=int(port))
if __name__=='__main__':
	app.run(debug=True )
	