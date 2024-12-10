from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user,logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
# from flask_wtf import FlaskForm
# from wtforms import StringField, PasswordField, SubmitField
# from wtforms.validators import Length, EqualTo, Email, DataRequired, ValidationError
from functools import wraps
from datetime import datetime


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///provider.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = '17ce2afd1bf4a1e4eecbfbdf'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view ="login"
db = SQLAlchemy(app)
class User(db.Model):
    username = db.Column(db.String(80), primary_key=True, unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)
# Service Provider Model
class Service_provider(UserMixin,db.Model):
    Fullname = db.Column(db.String(20), nullable=False)
    username = db.Column(db.String(80), primary_key=True, unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    service_name = db.Column(db.String(100), nullable=False)
    experience = db.Column(db.Integer, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pincode = db.Column(db.String(14), nullable=False)
    document_name = db.Column(db.String(250), nullable=False)
    document_data = db.Column(db.LargeBinary, nullable=False)
    status = db.Column(db.String(20), default='pending')
    def get_id(self):
        return self.username

# User Registration Model
class User_registeration(UserMixin,db.Model):
    Fullname = db.Column(db.String(20), nullable=False)
    username= db.Column(db.String(80), primary_key=True,unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pincode = db.Column(db.String(14), nullable=False)
    def get_id(self):
        return self.username

# Service Request Model
class request_service(db.Model):
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    Fullname = db.Column(db.String(20), nullable=False)
    Service_required = db.Column(db.String(100), nullable=False)
    Description = db.Column(db.String(200))
    Provider_username=db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending') 
    User_username=db.Column(db.String(20)) 
     # Link to a service provider
    service_provider_username = db.Column(db.String(80), db.ForeignKey('service_provider.username'), nullable=True)

    # Relationship to access the assigned service provider
    service_provider = db.relationship('Service_provider', backref='requests')

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200))

class AdminUser(UserMixin):
    id =1
    user_type ='admin' 

class BlockedUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    user_type = db.Column(db.String(50), nullable=False)
    blocked_at = db.Column(db.DateTime, default=datetime.utcnow)

    def _repr_(self):
        return f"<BlockedUser {self.username}>"


with app.app_context():
    db.create_all()
@login_manager.user_loader
def load_user(user_id):
    # Retrieve the user based on the user_id
    if(user_id=='1'):
        return AdminUser()
    else:
        user = Service_provider.query.get(user_id) or User_registeration.query.get(user_id)
        return user
         
    
@app.route('/')
@login_required
def home():
    print(session)
    if session['user_type'] == 'service_provider':
        # Get all service requests that are linked to the current provider
        service_requests = request_service.query.filter_by(Provider_username=session.get('username')).all()
        return render_template('provider_requests.html', requests=service_requests)
    elif session['user_type']=="user":
        user_request = request_service.query.filter_by(User_username=session.get('username')).all()
        return render_template('user_home.html',request=user_request)
    else:
        flash("You are not authorized to view this page", 'danger')
        return redirect(url_for('login'))

@app.route('/home')
def home_page():
    return render_template('home.html')
@app.route('/user_home')
def user_home():
    user_requests = request_service.query.filter_by(User_username=session.get('username')).all()
    return render_template('user_home.html',request=user_requests)
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.user_type != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# Route to add a new service
@app.route('/add_service', methods=['GET', 'POST'])
@login_required
def add_service():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        if not name:
            flash('Service name is required!', 'danger')
            return redirect(url_for('add_service'))

        # Debug output to see the data being received
        print(f"Received name: {name}, description: {description}")
        new_service = Service(name=name, description=description)
        db.session.add(new_service)
        db.session.commit()
        flash('New service added!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('/add_service.html')

# Route to view all users with block/unblock option
@app.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    # Get all users (service providers and regular users)

    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username')
        user_type = request.form.get('user_type')
        # Block the user
        if action == 'block':
            user = User_registeration.query.filter_by(username=username).first() or Service_provider.query.filter_by(username=username).first()
            if user:
                user.is_blocked = True
                db.session.commit()

                # Add to BlockedUser table
                blocked_user = BlockedUser(username=username, user_type=user_type)
                db.session.add(blocked_user)
                db.session.commit()

                flash(f"User {username} has been blocked.", 'success')
            else:
                flash(f"User {username} not found.", 'danger')

        # Unblock the user
        elif action == 'unblock':
            blocked_user = BlockedUser.query.filter_by(username=username).first()
            if blocked_user:
                # Remove from BlockedUser table
                db.session.delete(blocked_user)
                db.session.commit()

                # Update the User table to unblock
                user = User.query.filter_by(username=username).first()
                if user:
                    user.is_blocked = False
                    db.session.commit()

                flash(f"User {username} has been unblocked.", 'success')
            else:
                flash(f"Blocked user {username} not found.", 'danger')

        return redirect(url_for('manage_users'))

    return render_template('manage_users.html')

# Admin Dashboard
@app.route('/admin')
@login_required
def admin_dashboard():
    pending_service_providers = Service_provider.query.filter_by(status='pending').all()
    services = Service.query.all()
    return render_template('admin_dashboard.html', service_providers=pending_service_providers,services=services)
@app.route('/approve_service_provider/<username>', methods=['GET'])
@login_required
def approve_service_provider(username):
  

    service_provider = Service_provider.query.get(username)
    if service_provider and service_provider.status == 'pending':
        service_provider.status = 'approved'  # Change status to approved
        db.session.commit()
        flash(f'Service provider {username} approved.', 'success')
    else:
        flash('Service provider not found or already processed.', 'danger')

    return redirect(url_for('admin_dashboard'))

@app.route('/reject_service_provider/<username>', methods=['GET'])
@login_required
def reject_service_provider(username):

    service_provider = Service_provider.query.get(username)
    if service_provider and service_provider.status == 'pending':
        service_provider.status = 'rejected'  # Change status to rejected
        db.session.commit()
        flash(f'Service provider {username} rejected.', 'danger')
    else:
        flash('Service provider not found or already processed.', 'danger')

    return redirect(url_for('admin_dashboard'))

# Registration for Service Providers
@app.route('/register_Service_Provider', methods=['GET', 'POST'])
def registration_Service_Provider():
    if request.method == 'POST':
        Fullname = request.form['Fullname']
        username = request.form['username']
        password = request.form['password']
        service_name = request.form['service_name']
        experience = request.form['experience']
        address = request.form['address']
        pincode = request.form['pincode']
        document = request.files['document']
        hashed_password = generate_password_hash(password)

        if document and document.filename:
            document_name = document.filename
            document_data = document.read()  
        else:
            flash('Upload document', 'danger')
            return redirect(url_for('registration_Service_Provider'))
        result = Service.query.filter_by(name=service_name).first()
        if result:
            pass
        else:
            flash("This service is currently unavailable!!")
            return redirect(url_for('registration_Service_Provider'))
        new_service_provider = Service_provider(
            Fullname=Fullname,
            username=username,
            password=hashed_password,
            service_name=service_name,
            address=address,
            pincode=pincode,
            document_name=document_name,
            document_data=document_data,
            experience=experience,
            status='pending' 
        )
        db.session.add(new_service_provider)
        try:
            db.session.commit()
            flash(f'Service provider {username} registered successfully!', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash('Username already exists. Please go to login_page', 'danger')
            return redirect(url_for('registration_Service_Provider'))
    return render_template('register_service_provider.html')
# User Registration
@app.route('/register_user', methods=['GET', 'POST'])
def user_registration():
    if request.method == 'POST':
        Fullname = request.form['Fullname']
        username = request.form['username']
        password = request.form['password']
        address = request.form['address']
        pincode = request.form['pincode']

        existing_user = User_registeration.query.filter_by(username=username).first()
        if existing_user:
            flash("User already exists. Please log in!", 'danger')
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password)
        new_user = User_registeration(
            Fullname=Fullname,
            username=username,
            password=hashed_password,
            address=address,
            pincode=pincode
        )

        db.session.add(new_user)
        try:
            db.session.commit()
            flash(f'User {username} registered successfully!', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash('Username already exists. Please go to login_page', 'danger')
            return redirect(url_for('user_registration'))
    return render_template('register_user.html')
# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_type = request.form['user_type']
        print("here")
        
        if(BlockedUser.query.filter_by(username=username).first()):
            flash("You can not login!!")
            return redirect(url_for('home'))
        print(user_type)
        if (user_type == "admin"):
            if username =='Nitesh' and password=='Nitesh':
                admin=AdminUser()
                session['username'] = 'Nitesh'
                session['user_type'] = 'admin'
                login_user(admin)
                flash(f'Logged in successfully as {user_type}!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid creadentials','danger')
        elif(user_type=="Service_Provider"):
            service_provider=Service_provider.query.filter_by(username=username).first()
            if service_provider.status != 'approved':
                    flash('Your account is pending approval. Please wait for admin approval.', 'danger')
                    return redirect(url_for('home'))
            
            if service_provider and check_password_hash(service_provider.password,password):
                login_user(service_provider)
                session['username']=current_user.username
                session['user_type']="service_provider"
                flash(f'Logged in successfully as {user_type}! and as username {username}', 'success')
                return redirect(url_for('provider_requests'))
            else:
                flash('Invalid Password or username.Please try again.','danger')
                return redirect(url_for('home'))
        else:
             user_registration= User_registeration.query.filter_by(username=username).first()
             if user_registration and check_password_hash(user_registration.password, password):
            # Store username and user_type in session
                login_user(user_registration)
                session['username']=current_user.username
                session['user_type']="user"
                 # 'user' or 'service_provider'
                flash(f'Logged in successfully as {user_type}! and username as {username}', 'success')
                return redirect(url_for('home'))
             else:
                flash('Invalid username or password. Please try again.', 'danger')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/service', methods=['POST', 'GET'])
@login_required
def service():
    items = Service_provider.query.all()
    return render_template('service.html', items=items)
# Request Service
@app.route('/request_service', methods=['POST', 'GET']) 
def request_service_view():
    if request.method == 'POST':
        print(f"Fullname: {request.form.get('Fullname')}")
        Fullname = request.form['Fullname']
        Service_required = request.form['Service_required']
        Description = request.form['Description']
        Provider_username=request.form['Provider_username']
        User_username=request.form['User_username']
        new_request=request_service(Fullname=Fullname,Service_required=Service_required,Description=Description,Provider_username=Provider_username,
                                    User_username=User_username)
        try:
            db.session.add(new_request)
            db.session.commit()
            flash("Service request submitted successfully!", "success")
            return redirect(url_for('home'))
        except Exception as e:
            print(f"Error: {e}")  # Log the error
            flash("An error occurred while submitting the request.", "danger")
            db.session.rollback()
            return redirect(url_for('request_service_view'))
    return render_template('request_service.html',current_user=current_user)
# End Service Request by User
@app.route('/end_request/<int:request_id>', methods=['POST'])
def end_request(request_id):
    service_request = request_service.query.get(request_id)
    if not service_request:
        flash("Service request not found", 'danger')
        return redirect(url_for('home'))
    # Ensure the logged-in user is the one who created the request
    if session.get('username') != service_request.Fullname:
        flash("You cannot end this request", 'danger')
        return redirect(url_for('home'))
    service_request.status = 'completed_by_user'
    db.session.commit()
    flash("Service request ended successfully", 'success')
    return redirect(url_for('home'))
# Provider Actions: Accept or Reject Request
@app.route('/provider_request_action/<int:request_id>', methods=['POST'])
def provider_request_action(request_id):
    service_request = request_service.query.get(request_id)
    action = request.form.get('action')

    # Ensure the logged-in user is a service provider
    if session.get('user_type') != 'service_provider':
        flash("You are not authorized to perform this action", 'danger')
        return redirect(url_for('provider_requests'))

    action = request.form.get('action')  # 'accept' or 'reject'

    if action == 'reject':
        service_request.status = 'rejected_by_provider'
        db.session.commit()
        flash("Service request rejected", 'danger')

    elif action == 'accept':
        service_request.status = 'accepted_by_provider'
        service_request.Service_provider_username = session.get('username')
        db.session.commit()
        flash("Service request accepted and will be completed by the provider", 'success')
    return redirect(url_for('provider_requests'))
# Provider Request List
@app.route('/provider_requests')
@login_required
def provider_requests():
    # Only service providers should access this route
    if session.get('user_type') == 'service_provider':
        # Get all service requests that are linked to the current provider
        service_requests = request_service.query.filter_by(Provider_username=session.get('username')).all()
        return render_template('provider_requests.html', requests=service_requests)
    else:
        flash("You are not authorized to view this page", 'danger')
        return redirect(url_for('home'))
# search-bar
@app.route('/search',methods=['GET','POST'])
@login_required
def search():
    query = request.form.get('query','').strip()
    if query:
        service_results = Service_provider.query.filter(Service_provider.service_name.ilike(f"%{query}%")).all()
        pincode_results = Service_provider.query.filter(Service_provider.pincode.ilike(f"%{query}%")).all()

        return render_template('search_results.html', 
                               service_name=service_results, 
                               pincode=pincode_results, 
                               query=query) 
    flash("Please enter a search term." ,"warning")
    return redirect(url_for('home'))
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    item = request_service.query.get(id)
    if request.method == 'POST':
        new_description = request.form['description']
        item.Description = new_description  # Update the description
        db.session.commit()  # Commit changes to the database
        print("here")
        return redirect(url_for('home'))  # Redirect back to the index page with the updated table
    
    return render_template('edit_request.html', item=item) 
@app.route('/cancel_request/<int:id>', methods=['POST'])
def cancel_request(id):
    user = request_service.query.get(id)
    if user:
        # Update the status to 'Cancelled' (or whatever status you want)
        user.status = 'Cancelled_by_user'
        db.session.commit()
    
    # Redirect back to the user home or the relevant page
    return redirect(url_for('user_home')) 
@app.route('/complete_request/<int:id>', methods=['POST'])
def complete_request(id):
    user = request_service.query.get(id)
    if user:
        # Update the status to 'completed_by_provider'
        user.status = 'completed_by_provider'
        db.session.commit()  # Save the changes to the database

        flash('Request marked as completed by provider.', 'success')
    else:
        flash('Request not found.', 'danger')

    # Redirect back to the appropriate page (e.g., user home or provider requests)
    return redirect(url_for('home')) 
@app.route('/edit_services/<int:id>', methods=['GET', 'POST'])
def edit_service(id):
    service = Service.query.get_or_404(id)

    if request.method == 'POST':
        # Get the form data
        service.name = request.form['name']
        service.description = request.form['description']
        
        # Commit changes to the database
        try:
            db.session.commit()
            flash('Service updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except:
            db.session.rollback()
            flash('Error updating service. Please try again.', 'danger')

    return render_template('edit_services.html', service=service)
@app.route('/delete_service/<int:id>', methods=['GET'])
def delete_service(id):
    service = Service.query.get_or_404(id)

    try:
        db.session.delete(service)
        db.session.commit()
        flash('Service deleted successfully!', 'success')
    except:
        db.session.rollback()
        flash('Error deleting service. Please try again.', 'danger')
    
    return redirect(url_for('admin_dashboard'))
# Logout
@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
