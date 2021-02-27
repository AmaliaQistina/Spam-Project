from flask import Flask
from flask import Flask, render_template, redirect, url_for, request, session
from flask_mysqldb import MySQL
import pandas as pd
import numpy as np
import MySQLdb.cursors
import re
from werkzeug.debug import DebuggedApplication
import io
from http.client import IncompleteRead
import os
from importlib import reload
import MySQLdb
from getpass import getpass
from mysql.connector import connect, Error
import pymysql
import mysql

app = Flask(__name__)

# MainPage (login)
@app.route('/')
def index():
    return render_template('index.html')

# Google cloud sql
PASSWORD = ""
PUBLIC_IP_ADDRESS = "35.187.250.76"
DBNAME = "pythonlogin"
PROJECT_ID = "spamchecker"
INSTANCE_NAME = "spam-checker-project"
CONNECTION_NAME = "spamchecker:asia-southeast1:spam-checker-project"

db_user = os.environ.get('root')
db_password = os.environ.get('')
db_name = os.environ.get('pythonlogin')
db_connection_name = os.environ.get('spamchecker:asia-southeast1:spam-checker-project')

SECRET_KEY = 'spamfilter'
DATA_BACKEND = 'cloudsql'
PROJECT_ID = 'spamchecker'
CLOUDSQL_USER = 'root'
CLOUDSQL_PASSWORD = ''
CLOUDSQL_DATABASE = 'pythonlogin'
CLOUDSQL_CONNECTION_NAME = 'spamchecker:asia-southeast1:spam-checker-project'

LOCAL_SQLALCHEMY_DATABASE_URI = (
	'mysql+pymysql://{user}:{password}@localhost/{database}').format(
		user=CLOUDSQL_USER, password=CLOUDSQL_PASSWORD, database=CLOUDSQL_DATABASE)

LIVE_SQLALCHEMY_DATABASE_URI = (
	'mysql+pymysql://{user}:{password}@localhost/{database}'
	'?unix_socket=/cloudsql/{connection_name}').format(
		user=CLOUDSQL_USER, password=CLOUDSQL_PASSWORD, database=CLOUDSQL_DATABASE, connection_name=CLOUDSQL_CONNECTION_NAME)	

if os.environ.get('GAE_APPENGINE_HOSTNAME'):
	SQLALCHEMY_DATABASE_URI = LIVE_SQLALCHEMY_DATABASE_URI
else:
	SQLALCHEMY_DATABASE_URI = LIVE_SQLALCHEMY_DATABASE_URI

# for login
app.secret_key = 'spamfilter'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'pythonlogin'
app.config['MYSQL_CURSORCLASS'] = "DictCursor"

mysql = MySQL(app)

# http://localhost:5000/pythonlogin/
@app.route('/pythonlogin/', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password,))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            return redirect(url_for('home'))
        else:
            msg = 'You have enter the wrong username/password!'
    return render_template('index.html', msg=msg)

@app.route('/pythonlogin/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/pythonlogin/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form and 'fullname' in request.form and 'age' in request.form and 'phoneno' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        fullname = request.form['fullname']
        age = request.form['age']
        phoneno = request.form['phoneno']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email or not fullname or not age or not phoneno:
            msg = 'Please fill out the form!'
        else:
            cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s, %s, %s, %s)', (username, password, email, fullname, age, phoneno,))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
    elif request.method == 'POST':
        msg = 'Please fill out the form!'
    return render_template('register.html', msg=msg)

# http://localhost:5000/pythonlogin/home
@app.route('/pythonlogin/home', methods=['GET'])
def home():
    if 'loggedin' in session:
        return render_template('home.html', username=session['username'])
    return redirect(url_for('login'))   

@app.route('/pythonlogin/check')
def predict():
    return render_template('predict.html')

@app.route('/pythonlogin/check', methods=['POST'])
def check():
    url = "https://raw.githubusercontent.com/AmaliaQistina/Spam-Project/main/spam_dataset.csv"
    df= pd.read_csv(url, error_bad_lines=False)
    df_data = df[["CONTENT","LABEL"]]
    # Features and Labels
    df_x = df_data['CONTENT']
    df_y = df_data.LABEL
    # Extract Feature With CountVectorizer
    from sklearn.feature_extraction.text import CountVectorizer
    corpus = df_x
    cv = CountVectorizer() 
    X = cv.fit_transform(corpus) 
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, df_y, test_size=0.3, random_state=42)
    
    from sklearn.naive_bayes import MultinomialNB
    mnb = MultinomialNB()
    mnb.fit(X_train, y_train)
    mnb.score(X_test, y_test)
    if request.method == 'POST':
        comment = request.form['comment']
        data = [comment]
        vect = cv.transform(data).toarray()
        my_prediction = mnb.predict(vect)
    return render_template('results.html', prediction=my_prediction, comment=comment)

# http://localhost:5000/pythinlogin/profile
@app.route('/pythonlogin/profile')
def profile():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        return render_template('profile.html', account=account)
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
