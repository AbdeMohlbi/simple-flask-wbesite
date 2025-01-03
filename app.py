from flask import Flask, jsonify,redirect,url_for,render_template,request,session,flash
from datetime import timedelta,datetime
from dotenv import load_dotenv
import os
import mysql.connector
import random
import json
from urllib.parse import unquote
app= Flask(__name__)
app.secret_key = "the one who left it all behind and his overwhelming intensity"
app.permanent_session_lifetime=timedelta(days=1)
IMAGE_FOLDER = os.path.join(app.root_path, 'static', 'images')

load_dotenv()

db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT', 3306))  
}

def initialize_database():
    """Create tables if they don't already exist."""
    users_table = """
        CREATE TABLE IF NOT EXISTS `flask_app`.`clients` (
        `idClient` INT NOT NULL AUTO_INCREMENT,
        `clientName` VARCHAR(45) NOT NULL,
        `clientPassword` VARCHAR(45) NOT NULL,
        PRIMARY KEY (`idClient`, `clientName`),
        UNIQUE INDEX `idClient_UNIQUE` (`idClient` ASC) VISIBLE,
        UNIQUE INDEX `clientName_UNIQUE` (`clientName` ASC) VISIBLE);
    """
    products_table= """
        CREATE TABLE IF NOT EXISTS `flask_app`.`products` (
        `idProduct` INT NOT NULL AUTO_INCREMENT,
        `namesProduct` VARCHAR(20) NOT NULL,
        `descriptionProduct` VARCHAR(145) NOT NULL,
        `price` DECIMAL(10, 2) NOT NULL,
        PRIMARY KEY (`idProduct`, `namesProduct`),
        UNIQUE INDEX `idProduct_UNIQUE` (`idProduct` ASC) VISIBLE,
        UNIQUE INDEX `namesProduct_UNIQUE` (`namesProduct` ASC) VISIBLE);
    """
    sales_table= """
        CREATE TABLE IF NOT EXISTS sales (
        idSale INT AUTO_INCREMENT PRIMARY KEY,
        idClient INT NOT NULL,
        sale_datetime DATETIME NOT NULL,
        sale_data JSON NOT NULL,
        FOREIGN KEY (idClient) REFERENCES clients(idClient)
        );
    """
    stock_table= """
        CREATE TABLE IF NOT EXISTS stock (
        idProduct INT NOT NULL,
        quantiteProduct Int NOT Null,
        FOREIGN KEY (idProduct) REFERENCES products(idProduct)
        );
    """
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(users_table)
        cursor.execute(products_table)
        cursor.execute(sales_table)
        cursor.execute(stock_table)
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully.")
    except mysql.connector.Error as err:
        print(f"Error initializing database: {err}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


@app.before_request
def setup():
    """Run database initialization."""
    if not hasattr(app, 'db_initialized'):
        initialize_database()
        app.db_initialized = True  


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/shop")
def shop():
    if "username" in session:
        images = [f'quality{i}.png' for i in range(1, 9)]
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        for product in products:
            product['image'] = random.choice(images)
        conn.commit()
        cursor.close()
        conn.close()
        return render_template('shop.html', products=products)
    else:
        flash("u must log in first","info")
        return redirect(url_for('login'))

# from flask import jsonify, session
# from datetime import datetime
# import mysql.connector
# import json

@app.route('/purchase/<product_name>', methods=['POST'])
def purchase(product_name):
    # Decode the product name
    decoded_product_name = unquote(product_name)
    if "username" in session:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Fetch client ID
        search_query = "SELECT idClient FROM clients WHERE clientName = %s"
        cursor.execute(search_query, (session["username"],))
        result = cursor.fetchone()

        # Fetch product ID
        product_query = "SELECT idProduct FROM products WHERE namesProduct = %s"
        cursor.execute(product_query, (decoded_product_name,))
        result1 = cursor.fetchone()
        if result is None:
            return jsonify({"error": "Client not found"}), 404

        if result1 is None:
            return jsonify({"error": "Product not found"}), 404

        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Insert sale record
        query = """
        INSERT INTO sales (idClient, sale_datetime, sale_data)
        VALUES (%s, %s, %s)
        """
        sale_data = json.dumps({
            "item": decoded_product_name,
            "quantity": 1
        })
        cursor.execute(query, (result[0], current_datetime, sale_data))

        # Update stock
        query1 = """
        UPDATE stock
        SET quantiteProduct = quantiteProduct - 1
        WHERE idProduct = %s
        """
        cursor.execute(query1, (result1[0],))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": f"Purchase for {decoded_product_name} successful!"}), 200
    else:
        return jsonify({"error": "Unauthorized access"}), 401


@app.route("/admin")
def admin():
    # fetch data from the db

    sales_data = {
        'total_sales': '$12,000'
    }
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM clients")
    clients = cursor.fetchall()
    conn.commit()
    cursor.close()
    conn.close()
    return render_template("admin.html",total_sales=sales_data['total_sales'], clients=clients)

@app.route('/update_user', methods=['POST'])
def update_user():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    data = request.json
    print(data)
    user_id = data["id"]
    newusername = data['clientname']
    newpassword = data['clientPassword']
    
    # Update query
    update_query = """
            UPDATE clients
            SET clientName = %s, clientPassword = %s
            WHERE idClient = %s;
            """
    
    # Execute the update query
    cursor.execute(update_query, (newusername, newpassword, int(user_id)))

    # Commit the changes
    conn.commit()

    # Get the updated user data
    select_query = "SELECT * FROM clients WHERE idClient = %s;"
    cursor.execute(select_query, (int(user_id),))
    updated_user = cursor.fetchone()
    print(f"Updated User: {updated_user}")

    # Close the cursor and connection
    cursor.close()
    conn.close()

    print(f"Rows affected: {cursor.rowcount}")
    
    # Return JSON response indicating success
    return jsonify({"success": True, "message": "User updated successfully"}), 200



@app.route("/login",methods=["POST","GET"])
def login():
    if request.method=="POST":
        session.permanent=True
        username=request.form["username"]
        userpassword=request.form["password"]
        if username == "admin" and userpassword == "admin":
            session["username"]=username
            session["userpassword"]=userpassword
            return redirect(url_for("admin"))
        try: 
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            query = """
                SELECT * FROM flask_app.clients where clients.clientName= %s and clients.clientPassword= %s;;
            """
            cursor.execute(query, (username, userpassword))
            result = cursor.fetchone()
            if result==None:
                flash("no user with provided data exsits","info")
                return render_template("login.html")
            else:
                session["username"]=username
                session["userpassword"]=userpassword
                return redirect(url_for("user"))
        except mysql.connector.Error as err:
            return jsonify({"error": str(err)}), 500
    else:
        if "username" in session:
            return redirect(url_for("user"))
        return render_template("login.html")

@app.route("/user")
def user():
    if "username" in session:
        return f"<h1>{session["username"]}</h1>"
    else:
        return redirect(url_for("login"))
    

@app.route("/logout")
def logout():
    if "username" in session:
        flash("you have been logged out!","info")
    session.pop("username",None)
    session.pop("userpassword",None) 
    return redirect(url_for("login"))

if __name__=="__main__":
    app.run(debug=True)