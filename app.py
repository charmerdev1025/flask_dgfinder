import os
from flask import Flask, request, render_template,jsonify,redirect
from flaskext.mysql import MySQL
import hashlib
import time
import pandas as pd
import gspread
# from tika import parser
from pypdf import PdfReader
import mimetypes
import re
import numpy as np

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
@app.route('/sds')
def sds():
    query = "SELECT id, material_number, material_name, un_number, psn, hazard_label, sds_attached, sds_link, class_name, updated_at from sds"
    cursor.execute(query)
    data = cursor.fetchall()
    conn.commit()
    return render_template('sds.html', data=data)
@app.route('/sds/add')
def sds_add():
    return render_template('sds_add.html')
@app.route('/sds/edit', methods=['GET'])
def sds_edit():
    args = request.args
    id = args.get("id")
    query = "SELECT id, material_number, material_name, un_number, psn, hazard_label, sds_attached, sds_link, class_name, updated_at from sds where id=%s"
    cursor.execute(query, (id))
    data = cursor.fetchall()
    conn.commit()
    return render_template('sds_edit.html', data=data)

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

@app.route('/delete_sds', methods=['POST'])
def delete_sds():
    id = request.json["id"]
    sds_attached = request.json["sds_attached"]
    query = "delete from sds where id=%s"
    cursor.execute(query, (id))
    conn.commit()
    os.remove(os.path.join('static/uploads/sds', sds_attached))
    return jsonify({"result":"success"})

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
    # raw = parser.from_file('static' + target_path[1::])
    exclude_ws = sh.worksheet('Exclusion')
    exclude_df = pd.DataFrame(exclude_ws.get_all_records())
    exclude_list = []
    for row in exclude_df.values.tolist():
        exclude_item = row[0]
        exclude_item = exclude_item.strip()
        if exclude_item == "":
            break
        exclude_list.append(exclude_item.lower())
    # print(raw['content'])
    reader = PdfReader(target_path)
    content = ""
    for page in reader.pages:
        content += page.extract_text() + "\n"

    line_splits = content.split("\n")
    result = []
    words = []
    count = 0
    countArray = []
    
    for row in df.values.tolist():
        keywords = row[3].split(",")
        keywords = [keyword for keyword in keywords if len(keyword.strip()) > 1]
        for keyword in keywords:
            keyword_lower = keyword.strip().lower()

            checkKeyword = False
            keywordCount = 0
            if not keyword.isnumeric():
                for line in line_splits:
                    line_content = line.strip().lower()
                    if keyword_lower in line_content:
                        exclude_flag = False
                        for exclude_item in exclude_list:
                            if exclude_item in line_content:
                                exclude_flag = True
                                break
                        if exclude_flag == True:
                            continue

                    keyword_positions = [i for i in range(len(line_content)) if line_content.startswith(keyword_lower, i)]  
                    for key_pos in keyword_positions:
                        before_pos = key_pos - 1
                        after_pos = key_pos + len(keyword_lower)

                        before_check = False
                        after_check = False

                        if before_pos < 0:
                            before_check = True
                        else:
                            before_char = line_content[before_pos]
                            if before_char.isalpha() == False:
                                before_check = True
                        if after_pos >= len(line_content):
                            after_check = True
                        else:
                            after_char = line_content[after_pos]
                            if after_char.isalpha() == False:
                                after_check = True

                        if before_check == True and after_check == True:
                            keywordCount += 1
                            checkKeyword = True

            if checkKeyword == True:
                
                if not keyword.strip() in words:
                    words.append(keyword.strip())
                    result.append(row)
                    count += keywordCount
                    countArray.append(keywordCount)
                break
    return jsonify([result, words, countArray, count, imageLists])

@app.route('/sds_add_submit', methods = ['GET', 'POST'])
def sds_add_submit():
    if request.method == "POST":
        file = request.files['sds_attached']
        filename = file.filename
        targetFile	= str(time.time()) + "-" + filename.replace(" ","-").lower()
        file.save(os.path.join('static/uploads/sds', targetFile))
        material_number = request.form["material_number"]
        material_name = request.form["material_name"]
        un_number = request.form["un_number"]
        class_name = request.form["class_name"]
        psn = request.form["psn"]
        hazard_label = request.form["hazard_label"]
        sds_link = request.form["sds_link"]
        query = "insert into sds (un_number, psn, hazard_label, sds_attached, sds_link, material_number, material_name, class_name) values (%s,%s,%s,%s,%s,%s,%s,%s)"
        cursor.execute(query, (un_number, psn, hazard_label, targetFile, sds_link ,material_number, material_name, class_name))
        conn.commit()
        return redirect('/sds')
@app.route('/sds_edit_submit', methods = ['GET', 'POST'])
def sds_edit_submit():
    if request.method == "POST":
        file = request.files['sds_attached']
        existing_sds_attached = request.form["existing_sds_attached"]
        filename = file.filename
        targetFile	= str(time.time()) + "-" + filename.replace(" ","-").lower()
        id = request.form["sds_id"]
        material_number = request.form["material_number"]
        material_name = request.form["material_name"]
        un_number = request.form["un_number"]
        class_name = request.form["class_name"]
        psn = request.form["psn"]
        hazard_label = request.form["hazard_label"]
        sds_link = request.form["sds_link"]
        if filename == "":
            targetFile = existing_sds_attached
        else:
            os.remove(os.path.join('static/uploads/sds', existing_sds_attached))
            file.save(os.path.join('static/uploads/sds', targetFile))
        # print(targetFile)
        query = "update sds set un_number=%s, psn=%s, hazard_label=%s, sds_attached=%s, sds_link=%s, material_number=%s, material_name=%s, class_name=%s where id=%s"
        cursor.execute(query, (un_number, psn, hazard_label, targetFile, sds_link ,material_number, material_name, class_name, id))
        conn.commit()
        return redirect('/sds')
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



