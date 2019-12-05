from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from datetime import datetime, date
from calendar import monthrange, prevmonth, nextmonth
import ibm_db

app=Flask(__name__)

dsn_driver = "{IBM DB2 ODBC DRIVER}"
dsn_database = "BLUDB"            # e.g. "BLUDB"
dsn_hostname = "dashdb-txn-sbox-yp-lon02-02.services.eu-gb.bluemix.net" # e.g.: "awh-yp-small03.services.dal.bluemix.net"
dsn_port = "50000"                # e.g. "50000" 
dsn_protocol = "TCPIP"            # i.e. "TCPIP"
dsn_uid = "lwb20106"        # e.g. "dash104434"
dsn_pwd = "nng3vj3r9-s2rnmg"       # e.g. "7dBZ3wWt9XN6$o0JiX!m"

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
	month_length=monthrange(year,month)[1]
	ibm_db.close(conn)
	return render_template('schedule_table.html', month=month, year=year, month_name=month_name, year_name=year_name, month_length=month_length, shifts=shifts, team_members=team_members, team_name=team_name)

@app.route('/team/<string:team_name>/edit/schedule/<int:month>/<int:year>',methods=['GET','POST'])
def edit_schedule(team_name, month, year):
	#i am fetching shifts to prepopulate form
	shifts={}
	team_members=[]
	team={}
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
	month_length=monthrange(year,month)[1]
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
		return redirect(url_for('schedule',team_name=team_name, month=month, year=year))
	return render_template('edit_schedule_table.html', month=month, year=year, month_name=month_name, year_name=year_name, month_length=month_length, shifts=shifts, team_members=team_members, team_name=team_name)

@app.route('/next_month/<string:team_name>/<int:month>/<int:year>', methods=['POST'])
def next_month(team_name, month, year):
	variable=nextmonth(year,month)
	year=variable[0]
	team_name=team_name
	month=variable[1]
	return redirect(url_for('schedule', team_name=team_name, month=month, year=year, ))

@app.route('/prev_month/<string:team_name>/<int:month>/<int:year>', methods=['POST'])
def prev_month(team_name, month, year):
	variable=prevmonth(year,month)
	year=variable[0]
	team_name=team_name
	month=variable[1]
	return redirect(url_for('schedule', team_name=team_name, month=month, year=year ))

if __name__=='__main__':
	app.secret_key='secret123'
	app.run(debug=True)