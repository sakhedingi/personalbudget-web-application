import mysql.connector
from flask import Flask, redirect, render_template, request, session, url_for
from flask_session import Session

import bcrypt

# Configure application
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_PASSWORD'] = 'admin'
app.config['MYSQL_DB'] = 'personal_budget'

mysql = mysql.connector.connect(
    host=app.config['MYSQL_HOST'],
    user=app.config['MYSQL_USER'],
    port=app.config['MYSQL_PORT'],
    password=app.config['MYSQL_PASSWORD'],
    database=app.config['MYSQL_DB']
)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route('/')
def index():
    # Redirect to the login page
    return redirect(url_for('login'))

@app.route("/home")
def home():
    """Show portfolio of stocks"""
    if 'username' in session:
        username = session["username"]

        cursor = mysql.cursor()
        cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
        user = cursor.fetchone()

        if user is not None:
            user_id = user[0]

            cursor.execute("SELECT SUM(amount) AS totalIncome FROM income INNER JOIN users ON income.user_id = %s AND users.id = %s", (user_id, user_id))
            totalIncome = cursor.fetchone()[0]

            cursor.execute("select SUM(amount) as totalExpenses from expenses inner join users on expenses.user_id = %s and users.id = %s", (user_id, user_id))
            totalExpenses = cursor.fetchone()[0]

            if totalExpenses is not None:
                balance = totalIncome - totalExpenses
            else:
                totalExpenses = 0.00
                totalExpenses = "{:.2f}".format(totalExpenses)
                balance = totalIncome

            cursor.close()

            return render_template("home.html", username=username, totalIncome=totalIncome, totalExpenses=totalExpenses, balance=balance)
    return render_template('login.html')

@app.route("/expenses", methods=["GET", "POST"])
def expenses():
    """Track expenses"""
    if 'username' in session:
        username = session['username']
        cursor = mysql.cursor()

        cursor.execute(f"SELECT id FROM users WHERE username = '{username}'")
        user_id = cursor.fetchone()[0]

        cursor.execute("select description, category, amount, date from expenses where user_id = %s", (user_id,))
        expenses = cursor.fetchall()

        cursor.close()
        return render_template('expenses.html', expenses=expenses)
    return redirect(url_for('home'))

@app.route("/admin", methods=["GET", "POST"])
def admin():
    """Admin"""
    if 'username' in session:
        username = session['username']
        return render_template('admin.html', username=username)
    return redirect(url_for('home'))

@app.route("/account", methods=["GET", "POST"])
def account():
    """User account"""
    if 'username' in session:
        username = session['username']
        cursor = mysql.cursor()

        cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
        user = cursor.fetchone()
        cursor.close()

        if user is not None:
            return render_template('account.html', user=user)
        return redirect(url_for('logout'))


@app.route("/search", methods=["GET", "POST"])
def search():
    """Search users"""
    if request.method == "POST":
        cursor = mysql.cursor()

        search_id = request.form["search"]

        print("search id: ",search_id)

        cursor.execute(f"SELECT * FROM users WHERE id = '{search_id}'")
        users = cursor.fetchall()
        cursor.close()

        session['search_id'] = search_id

        return render_template('admin.html', users=users)
    return redirect(url_for('home'))

@app.route("/delete", methods=["GET", "POST"])
def delete():
    """Delete users"""
    search_id = session.get('search_id')
    
    if request.method == "POST":
        if search_id:
            cursor = mysql.cursor()

            cursor.execute(f"DELETE FROM income WHERE user_id = '{search_id}'")
            mysql.commit()
            cursor.execute(f"DELETE FROM expenses WHERE user_id = '{search_id}'")
            mysql.commit()
            cursor.execute(f"DELETE FROM users WHERE id = '{search_id}'")
            mysql.commit()

            cursor.close()
            return render_template('admin.html')
        else:
            return render_template('admin.html')
    else:
        return render_template('admin.html')
    
@app.route("/deleteAccount", methods=["GET", "POST"])
def deleteAccount():
    """Delete user accounts"""
    if request.method == "POST":
        if 'username' in session:
            username = session['username']
            cursor = mysql.cursor()

            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            if user:
                user_id = user[0]

                cursor.execute("DELETE FROM income WHERE user_id = %s", (user_id,))
                cursor.execute("DELETE FROM expenses WHERE user_id = %s", (user_id,))
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                mysql.commit()

                session.pop('username', None)

            cursor.close()

            return render_template('account.html', user=None)
        else:
            return render_template('account.html', user=None)
    else:
        return render_template('account.html', user=None)

    
@app.route("/updateAccount", methods=["GET", "POST"])
def updateAccount():
    """Update users"""    
    if request.method == "POST":
        if 'username' in session:
            username = session['username']
            new_pwd = request.form["newpassword"]
            confirm_new_pwd = request.form["confirmation"]
            cursor = mysql.cursor()

            cursor.execute(f"SELECT id FROM users WHERE username = '{username}'")
            id = cursor.fetchone()[0]

            if new_pwd == confirm_new_pwd:
                print("")
            else:
                error = "Confirm password don not match"
                return render_template('account.html', error=error)

            def hash_password(new_pwd):
                salt = bcrypt.gensalt()
                hashed_pwd = bcrypt.hashpw(new_pwd.encode('utf-8'), salt)
                return hashed_pwd
                
            new_hashed_pwd = hash_password(new_pwd)

            cursor.execute("UPDATE users SET password = %s WHERE id = %s", (new_hashed_pwd, id))
            mysql.commit()

            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            cursor.close()

            return render_template('account.html', user=user)
        else:
            return render_template('login.html')
    else:
        return render_template('account.html')
        

@app.route("/income", methods=["GET", "POST"])
def income():
    """Track income"""
    if 'username' in session:
        username = session['username']
        cursor = mysql.cursor()

        cursor.execute(f"SELECT id FROM users WHERE username = '{username}'")
        user_id = cursor.fetchone()[0]

        cursor.execute("select source, amount, date from income where user_id = %s", (user_id,))
        incomes = cursor.fetchall()

        cursor.close()
        return render_template('income.html', incomes=incomes)
    return redirect(url_for('home'))

@app.route('/add_expense', methods=['POST'])
def add_expense():
    if 'username' in session:
        username = session['username']
        cursor = mysql.cursor()

        cursor.execute(f"SELECT id FROM users WHERE username = '{username}'")
        user_id = cursor.fetchone()[0]

        description = request.form['description']
        category = request.form['category']
        amount = request.form['amount']

        cursor.execute("INSERT INTO expenses (user_id, description, category, amount) VALUES (%s, %s, %s, %s)", (user_id, description, category, amount))
        mysql.commit()

        cursor.close()

        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/add_income', methods=['POST'])
def add_income():
    if 'username' in session:
        username = session['username']
        cursor = mysql.cursor()

        cursor.execute(f"SELECT id FROM users WHERE username = '{username}'")
        user_id = cursor.fetchone()[0]

        source = request.form['source']
        amount = request.form['amount']

        cursor.execute("INSERT INTO income (user_id, source, amount) VALUES (%s, %s, %s)", (user_id, source, amount))
        mysql.commit()

        cursor.close()

        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    if request.method == "POST":
        
        username = request.form["username"]
        pwd = request.form["password"]

        cursor = mysql.cursor()
        cursor.execute(f"SELECT username, password FROM users WHERE username = '{username}'")
        user = cursor.fetchone()
        cursor.close()

        if user:
            hashed_pwd = user[1].encode('utf-8')
            is_verified = bcrypt.checkpw(pwd.encode('utf-8'), hashed_pwd)

            if is_verified:
                session['username'] = user[0]
                return redirect(url_for('home'))  # Redirect to index instead of login
            else:
                error = 'Invalid username or password'
                return render_template('login.html', error=error)
        else:
            error = 'Invalid username or password'
            return render_template('login.html', error=error)

    return render_template('login.html')


@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
            username = request.form["username"]
            pwd = request.form["password"]
            confirm_pwd = request.form["confirmation"]

            if pwd == confirm_pwd:
                print("")
            else:
                error = "Confirm password don not match"
                return render_template('register.html', error=error)

            def hash_password(pwd):
                salt = bcrypt.gensalt()
                hashed_pwd = bcrypt.hashpw(pwd.encode('utf-8'), salt)
                return hashed_pwd
                
            hashed_pwd = hash_password(pwd)

            cash = request.form["cash"]

            if not cash:
                cash = 0.00

            cursor = mysql.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_pwd))
            mysql.commit()

            cursor.execute(f"SELECT id FROM users WHERE username = '{username}'")
            user_id = cursor.fetchone()[0]

            cursor.execute("INSERT INTO income (user_id, source, amount) VALUES (%s, %s, %s)", (user_id, "Cash", cash))
            mysql.commit()
            cursor.close()
            return redirect(url_for('login'))
    return render_template('register.html')

def my_view(request):
    # Determine the active endpoint (e.g., '/login', '/signup', etc.)
    active_endpoint = request.path
    print("active_endpoint", active_endpoint)
    # Other view logic...
    return render_template(request, 'layout.html', {'active_endpoint': active_endpoint})

