from flask import Flask, render_template, redirect, url_for, request, session,flash
from flask import send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from datetime import datetime
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
app.secret_key = 'supersecretkey'
app.secret_key = 'singh'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/Management'
db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    designation = db.Column(db.String(100), nullable=True)
    tasks = db.relationship('Task', backref='employee', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    file_url = db.Column(db.String(200), nullable=True)
    employee_comments = db.Column(db.Text, nullable=True)
    
class Approval(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(50), nullable=False)


    
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        mobile = request.form['mobile']
        dob = request.form['dob']
        designation = request.form['designation']  # Get the designation from the form

        # Convert the date string from the form (YYYY-MM-DD) to a datetime object
        new_employee = Employee(
            full_name=full_name,
            email=email,
            password=password,
            mobile=mobile,
            dob=datetime.strptime(dob, '%Y-%m-%d'),  # Corrected date format
            designation=designation  # Save the designation
        )
        db.session.add(new_employee)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if email == 'admin@gmail.com' and password == '12345':
            session['employee_id'] = 'admin'
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))

        employee = Employee.query.filter_by(email=email, password=password).first()
        if employee:
            session['employee_id'] = employee.id
            flash('Login successful!', 'success')
            return redirect(url_for('employee_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')





@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'employee_id' not in session or session['employee_id'] != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    # Check for overdue tasks
    overdue_tasks = Task.query.filter(Task.due_date < datetime.now(), Task.is_completed == False).all()
    if overdue_tasks:
        flash('Some tasks are overdue. Please check the task list.', 'warning')

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        due_date_str = request.form['due_date']
        employee_id = request.form['employee_id']

        file = request.files.get('file')
        file_url = None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            file_url = url_for('uploaded_file', filename=filename)

        try:
            due_date_date = datetime.strptime(due_date_str, '%d/%m/%Y').date()
            current_time = datetime.now().time()
            due_date = datetime.combine(due_date_date, current_time)
        except ValueError:
            flash('Invalid date format. Please use DD/MM/YYYY', 'danger')
            return redirect(url_for('admin_dashboard'))

        new_task = Task(
            title=title,
            description=description,
            due_date=due_date,
            employee_id=employee_id,
            file_url=file_url
        )
        db.session.add(new_task)
        db.session.commit()
        flash('Task assigned successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    # Fetch data for dashboard
    total_employees = Employee.query.count()
    tasks_assigned = Task.query.count()
    pending_approvals = Approval.query.filter_by(status='pending').count()

    employees = Employee.query.all()
    tasks = Task.query.all()

    return render_template('admin_dashboard.html',
                           total_employees=total_employees,
                           tasks_assigned=tasks_assigned,
                           pending_approvals=pending_approvals,
                           employees=employees,
                           tasks=tasks)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/employee_dashboard')
def employee_dashboard():
    if 'employee_id' not in session or session['employee_id'] == 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    employee_id = session['employee_id']
    tasks = Task.query.filter_by(employee_id=employee_id).all()
    return render_template('employee_dashboard.html', tasks=tasks)


@app.route('/submit_task/<int:task_id>', methods=['GET', 'POST'])
def submit_task(task_id):
    if 'employee_id' not in session or session['employee_id'] == 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    task = Task.query.get_or_404(task_id)
    if request.method == 'POST':
        file = request.files.get('file')
        comments = request.form.get('comments')
        file_url = task.file_url  # Keep existing file_url if no new file is uploaded

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            file_url = url_for('uploaded_file', filename=filename)

        # Update task with completion status, file_url, and employee comments
        task.is_completed = True
        task.file_url = file_url
        task.employee_comments = comments
        db.session.commit()
        flash('Task submitted successfully!', 'success')
        return redirect(url_for('employee_dashboard'))

    return render_template('task_submission.html', task=task)


@app.route('/assign_salary/<int:task_id>', methods=['GET', 'POST'])
def assign_salary(task_id):
    task = Task.query.get(task_id)
    if not task:
        flash('Task not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        salary = request.form['salary']
        if not salary:
            flash('Salary cannot be empty.', 'danger')
            return redirect(url_for('assign_salary', task_id=task_id))
        
        employee = task.employee
        employee.salary = salary
        db.session.commit()
        
        flash('Salary assigned successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('assign_salary.html', task=task)


@app.route('/logout')
def logout():
    session.pop('employee_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/assign_task', methods=['GET', 'POST'])
def assign_task():
        overdue_tasks = Task.query.filter(Task.due_date < datetime.now(), Task.is_completed == False).all()
        if overdue_tasks:
            flash('Some tasks are overdue. Please check the task list.', 'warning')

        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            due_date_str = request.form['due_date']
            employee_id = request.form['employee_id']

            file = request.files.get('file')
            file_url = None

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                file_url = url_for('uploaded_file', filename=filename)

            try:
        
                due_date_date = datetime.strptime(due_date_str, '%d/%m/%Y').date()
    
                current_time = datetime.now().time()
        
                due_date = datetime.combine(due_date_date, current_time)
            except ValueError:
                flash('Invalid date format. Please use DD/MM/YYYY', 'danger')
                return redirect(url_for('admin_dashboard'))
            new_task = Task(
                title=title,
                description=description,
                due_date=due_date,
                employee_id=employee_id,
                file_url=file_url
            )
            db.session.add(new_task)
            db.session.commit()
            flash('Task assigned successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        
        # Get the list of employees for the form
        employees = Employee.query.all()
        return render_template('assign_task.html', employees=employees)




if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    app.run(debug=True)
