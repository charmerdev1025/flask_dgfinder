import os
from flask import Flask, request, render_template,jsonify
from flaskext.mysql import MySQL
import hashlib
import time
import pandas as pd
import gspread
import re
import numpy as np
# from tika import parser
from pypdf import PdfReader
import mimetypes
# import fitz

# import PyPDF3
# import tabula

mimetypes.add_type('application/javascript', '.js', True)
mimetypes.add_type('text/css', '.css')

app = Flask(__name__)
mysql = MySQL()

app.config['MYSQL_DATABASE_HOST'] = 'localhost'
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'dgfinder'
mysql.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/login')
def login():
    return render_template('login.html')
@app.route('/home')
def home():
    return render_template('home.html')
@app.route('/compatibility')
def compatibility():
    return render_template('compatibility.html')

@app.route('/db_login', methods=['POST'])
def db_login():
    email = request.json["email"]
    password = request.json["password"]
    password = hashlib.sha1(password.encode('utf-8')).hexdigest()
    query = "SELECT * from users where email=%s and password=%s"
    cursor.execute(query, (email, password))
    data = cursor.fetchone()
    conn.commit()
    result = "fail"
    if cursor.rowcount == 1:
        result = "success"

    return jsonify({"result":result})

@app.route('/upload', methods = ['POST'])
def upload():
    file = request.files['file']
    filename = file.filename
    targetFile	= str(time.time()) + "-" + filename.replace(" ","-").lower()
    target_path = "static/uploads/" + targetFile
    file.save(os.path.join('static/uploads', targetFile))
    return target_path
@app.route('/search', methods = ['POST'])
def search():
    target_path = request.json["filename"]
    imagePath = 'static/images/Hazard_labels'
    files = list(set(os.scandir(path=imagePath)) - set(['.', '..']))
    imageLists = []
    for file in files:
        imageLists.append(file.name)
    gc = gspread.service_account(filename='credentials.json')
    sh = gc.open_by_url('https://docs.google.com/spreadsheets/d/1fLzXr4Yw7WCQr4YQ_vM0UmYn17gXA05Yl94XlrEdPRk/edit#gid=0')
    ws = sh.worksheet('Sheet1')

    df = pd.DataFrame(ws.get_all_records())

    content = ""
    reader = PdfReader(target_path)
    for page in reader.pages:
        content += page.extract_text() + "\n"
    # doc = fitz.open(target_path)
    # for page in doc:
    #     content += page.get_text()
    result = []
    words = []
    count = 0
    countArray = []
    checkKeyword = False

    for row in df.values.tolist():
        keywords = row[3].split(",")
        keywords = [keyword for keyword in keywords if len(keyword.strip()) > 1]
        for keyword in keywords:
            if not keyword.isnumeric():
                if keyword.lower() in content.lower(): 
                    checkKeyword = True
                    result.append(row)
                    if not keyword in words:
                        count = count + content.lower().count(keyword.lower())
                        words.append(keyword)
                        countArray.append(content.lower().count(keyword.lower()))
                    break
    return jsonify([result, words, countArray, count, imageLists])

@app.route('/search_compatibility', methods = ['POST'])
def search_compatibility():
    target_path = request.json["filename"]
    imagePath = 'static/images/Hazard_labels'
    files = list(set(os.scandir(path=imagePath)) - set(['.', '..']))
    imageLists = []
    for file in files:
        imageLists.append(file.name)
    gc = gspread.service_account(filename='credentials.json')
    sh1 = gc.open_by_url('https://docs.google.com/spreadsheets/d/1fLzXr4Yw7WCQr4YQ_vM0UmYn17gXA05Yl94XlrEdPRk/edit#gid=0')
    ws1 = sh1.worksheet('Sheet1')
    df1 = pd.DataFrame(ws1.get_all_values())
    sh4 = gc.open_by_url('https://docs.google.com/spreadsheets/d/1fLzXr4Yw7WCQr4YQ_vM0UmYn17gXA05Yl94XlrEdPRk/edit#gid=320903526')
    ws4 = sh4.worksheet('Sheet4')
    df4 = pd.DataFrame(ws4.get_all_values())

    # raw = parser.from_file('static' + target_path[1::])
    # print(raw['content'])
    content = ""
    reader = PdfReader(target_path)
    for page in reader.pages:
        content += page.extract_text(0) + "\n"
    # doc = fitz.open(target_path)
    # for page in doc:
    #     content += page.get_text()
    result = []
    un_numbers = []
    classes = []
    for row in df1.values.tolist():
        un_number = row[1]
        if str(un_number) in content.lower():
            for compatibility in df4.values.tolist():
                real_class = str(row[4]).split(" ", 1)
                if str(real_class[0]) == compatibility[0].strip():
                    row.append(compatibility[1].strip())
                    row.append(compatibility[2].strip())
                    break
            if len(row) == 6:
                row.append("")
                row.append("")        
            result.append(row)
            classes.append(str(row[4]))
            un_numbers.append(un_number)
    classes = np.array(classes)        
    _, idx = np.unique(classes, return_index=True)
    classes = classes[np.sort(idx)].tolist()
    return jsonify([result, un_numbers, imageLists, classes, target_path])

if __name__ == '__main__':
    app.run(debug=True)

