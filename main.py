from flask import Flask, render_template, request, flash, redirect
from werkzeug.utils import secure_filename
import os
import chardet
from flask_sqlalchemy import SQLAlchemy
import pickle
import pandas as pd
from datetime import date,datetime


app = Flask(__name__)
app.secret_key = 'andndvi@r43r2111rfknasnksdywe202aajnvallkdnncsk'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///productvity.db'
db = SQLAlchemy(app)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class Productivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entry_date = db.Column(db.Date)
    quarters = db.Column(db.String(50))
    team = db.Column(db.Integer)
    targeted_productivity = db.Column(db.Float)
    smv = db.Column(db.Float)
    over_time = db.Column(db.Integer)
    incentive = db.Column(db.Integer)
    idle_time = db.Column(db.Integer)
    idle_men = db.Column(db.Integer)
    no_of_style_change = db.Column(db.Integer)
    no_of_workers = db.Column(db.Integer)
    dept_finishing = db.Column(db.Integer)
    dept_sweing = db.Column(db.Integer)
    prediction = db.Column(db.Float)

    def __init__(self, **kwargs):
        super(Productivity, self).__init__(**kwargs)


# Load your trained model
with open('finalized_model.pkl', 'rb') as f:
    model = pickle.load(f)

ALLOWED_EXTENSIONS = {'csv','xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    return render_template("home.html")

@app.route("/singleparameter", methods=["GET", "POST"])
def singleparameter():
    prediction = None
    if request.method == "POST":
        entry_date_str = request.form.get('entry_date')
        year, month, day = map(int, entry_date_str.split('-'))
        entry_date_obj = date(year, month, day)
        full_data = {
            'quarters': str(request.form.get('quarter')),
            'entry_date': entry_date_obj,
            'team': int(request.form.get('team')),
            'targeted_productivity': float(request.form.get('targeted_productivity')),
            'smv': float(request.form.get('smv')),
            'over_time': int(request.form.get('over_time')),
            'incentive': int(request.form.get('incentive')),
            'idle_time': int(request.form.get('idle_time')),
            'idle_men': int(request.form.get('idle_men')),
            'no_of_style_change': int(request.form.get('no_of_style_change')),
            'no_of_workers': int(request.form.get('no_of_workers')),
            'dept_finishing': 1 if request.form.get('department') == 'Finishing' else 0,
            'dept_sweing': 1 if request.form.get('department') == 'Sweing' else 0
        }

        model_data = {key: full_data[key] for key in full_data if key not in ['quarters', 'entry_date']}
        df = pd.DataFrame(model_data, index=[0])
        prediction = model.predict(df)[0]
        
        # Store data in the database
        new_entry = Productivity(**full_data, prediction=prediction)
        db.session.add(new_entry)
        db.session.commit()

    # Get the last saved data from the database to display in the form
    last_data = Productivity.query.order_by(Productivity.id.desc()).first()
    
    return render_template("Single.html", prediction=prediction, last_data=last_data, current_date=date.today())

@app.route("/multipleprediction", methods=["GET", "POST"])
def multipleprediction():
    rows_with_predictions = []

    if request.method == "POST":
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            file_extension = filename.rsplit('.', 1)[1].lower()

            if file_extension == 'csv':
                with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'rb') as rawdata:
                    result = chardet.detect(rawdata.read())
                df = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], filename), encoding=result['encoding'])
            elif file_extension in ['xlsx', 'xls']:
                df = pd.read_excel(os.path.join(app.config['UPLOAD_FOLDER'], filename), engine='openpyxl')
            else:
                flash('Unsupported file type.')
                return redirect(request.url)

            for _, row in df.iterrows():
                row_data = row.to_dict()

                if 'ENTRY_DATE' in row_data:
                    date_obj = pd.to_datetime(row_data['ENTRY_DATE']).date()
                    row_data['entry_year'] = date_obj.year
                    row_data['entry_month'] = date_obj.month
                    row_data['entry_day'] = date_obj.day
                    del row_data['ENTRY_DATE']

                row_data = {key.lower(): value for key, value in row_data.items()}
                            
                # Remove 'entry_date' since it's not a float or int.
                if 'entry_date' in row_data:
                    del row_data['entry_date']

                model_data = {key: value for key, value in row_data.items() if key not in ['quarters', 'entry_year', 'entry_month', 'entry_day']}
                df_single = pd.DataFrame(model_data, index=[0])

                prediction = model.predict(df_single)[0]
                row_data['prediction'] = prediction
                rows_with_predictions.append(row_data)

                new_entry_data = {key: value for key, value in row_data.items() if key not in ['entry_year', 'entry_month', 'entry_day']}
                new_entry = Productivity(**new_entry_data)
                db.session.add(new_entry)
                db.session.commit()

    return render_template("multiple.html", predictions=rows_with_predictions)


with app.app_context():
    db.create_all()

if __name__ == "__main__": 
    app.run(host = '0.0.0.0', port = 8080, debug = True)
