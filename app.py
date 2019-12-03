from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from datetime import datetime, date
from calendar import monthrange, prevmonth, nextmonth
import ibm_db

app=Flask(__name__)





if __name__=='__main__':
    app.secret_key='secret123'
    app.run(debug=True)