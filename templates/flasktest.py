from flask import Flask, redirect, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
import json
from flask_mail import Mail, Message
from datetime import datetime


with open('config.json', 'r') as c:
    params = json.load(c)["params"]

local_server=True
app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = '465',
    MAIL_USE_SSL = True,
    MAIL_USERNAME = params['gmail-user'],
    MAIL_PASSWORD = params['gmail-password']
)
mail = Mail(app)
if(local_server):
    app.config["SQLALCHEMY_DATABASE_URI"] = params['local_uri']
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = params['prod_uri']
db = SQLAlchemy(app)

class Customer (db.Model):
    Sno = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(80), nullable=False)
    Phone = db.Column(db.String(12), unique=True, nullable=False)
    Address = db.Column(db.String(120), nullable=False)
    Date = db.Column(db.DateTime, nullable=False)


class Items (db.Model):
    Sno = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(80), nullable=False)
    Price = db.Column(db.Integer, unique=True, nullable=False)
    image_url = db.Column(db.String(120), nullable=False)
    Date = db.Column(db.DateTime, nullable=False)


@app.route("/")
def index():
    return render_template('index.html', params = params)


@app.route("/admin", methods=['GET','POST'])
def admin(): 
    if request.method=='POST':
        username=request.form.get('username')
        password=request.form.get('password')
        if (username == params['admin_user'] and password == params['admin_password']):
            session['user'] = username
            return redirect('/adminpage')
        else:
            msg="Invalid Username or Password"
            return render_template("admin.html", msg=msg, params = params)
    return render_template("admin.html", params = params)


@app.route("/items", methods = ['GET'])
def items_all():
    data = Items.query.all()
    return render_template('items.html', params = params, data = data)


@app.route("/order", methods=['GET', 'POST'])
def order():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        village = request.form.get('village')

        # Retrieve cart items and total from session storage
        cartItems = json.loads(session.get('cartItems', '[]'))
        cartTotal = session.get('cartTotal', '₹0')

        subject = 'New Order From ' + name
        sender = params['gmail-user']
        recipients = [sender]

        body = f'''
            <html>
            <head></head>
            <body>
                <h2>Customer Information:</h2>
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Phone:</strong> {phone}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Address:</strong> {village}</p>

                <h2>Order Summary:</h2>
                <table border="1">
                    <thead>
                        <tr>
                            <th>Item Name</th>
                            <th>Quantity</th>
                            <th>Price</th>
                            <th>Total Price</th>
                        </tr>
                    </thead>
                    <tbody>
        '''

        for item in cartItems:
            body += f'''
                <tr>
                    <td>{item['name']}</td>
                    <td>{item['quantity']}</td>
                    <td>₹{item['price']}</td>
                    <td>₹{item['totalPrice']}</td>
                </tr>
            '''

        body += f'''
                    </tbody>
                    <tfoot>
                        <tr>
                            <td colspan="3">Total:</td>
                            <td>{cartTotal}</td>
                        </tr>
                    </tfoot>
                </table>
            </body>
            </html>
        '''

        msg = Message(subject=subject, sender=sender, recipients=recipients)
        msg.html = body
        mail.send(msg)
        
        session['cartItems'] = '[]'
        session['cartTotal'] = '₹0'

        return render_template('order.html', params=params, cartItems=cartItems, cartTotal=cartTotal)

    return render_template('order.html', params=params)


@app.route("/edit/<string:Sno>", methods=['GET', 'POST'])
def edit(Sno):
    if ('user' in session and session['user'] == params['admin_user']):
        if request.method == 'POST':
            P_name = request.form.get('Name')
            P_price = request.form.get('Price')
            P_image = request.form.get('image_url')

            if Sno != '0':
                item = Items.query.filter_by(Sno=Sno).first()
                item.Name = P_name
                item.Price = P_price
                item.image_url = P_image
                db.session.commit()
                return redirect('/edit/'+Sno)

        item = Items.query.filter_by(Sno=Sno).first()
        return render_template('edit.html', params=params, item=item)
    return render_template('edit.html', params=params, item=None, Sno=Sno)



@app.route("/about")
def review():
    return render_template('about.html', params = params)


@app.route("/delete/<string:Sno>", methods = ['GET', 'POST'])
def delete(Sno):
    if ('user' in session and session['user'] == params['admin_user']):
        items = Items.query.filter_by(Sno=Sno).first()
        db.session.delete(items)
        db.session.commit()
    return redirect('/adminpage')

@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/admin')



@app.route("/adminpage", methods = ['GET', 'POST'])
def adminpage():
    # Check if the user is authenticated (logged in)
    if 'user' not in session or session['user'] != params['admin_user']:
        return redirect('/admin')
    
    item = Items.query.all()

    if request.method == 'POST':
        Name = request.form.get('Name')
        Price = request.form.get('Price')
        image_url = request.form.get('image_url')
        entry = Items(Name=Name, Price=Price, image_url=image_url, Date=datetime.now())
        db.session.add(entry)
        db.session.commit()
    return render_template('adminpage.html', params = params, item = item)
    

if __name__ == "__main__":
    app.run(debug=True)