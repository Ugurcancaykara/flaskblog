from functools import wraps
from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL#mysql i dahil ediyoruz.
from wtforms import Form,StringField,TextAreaField,PasswordField,validators#formlar için gerekli modüller
from passlib.handlers.sha2_crypt import sha256_crypt

#kullanıcı giriş decorator'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Giriş yapınız !","danger")
            return redirect(url_for("login"))
    return decorated_function
#Kullanıcı kayıt formu
class RegisterForm(Form):
    name = StringField("İsim ve Soyisim: ",validators=[validators.Length(min = 4,max = 25)])
    username = StringField("Kullanıcı adı: ",validators=[validators.Length(min = 4,max = 30)])
    email = StringField("Email: ",validators=[validators.Email(message="Geçerli bir email adresi giriniz.")])
    password = PasswordField("Parola: ",validators=[
        validators.DataRequired(message="Geçerli bir parola giriniz."),
        validators.EqualTo(fieldname="confirm",message="Girdiğiniz parolalar aynı değil")

    ])
    confirm = PasswordField("Parola: ")
class LoginForm(Form):
    username = StringField("Kullanıcı adı: ")
    password = PasswordField("Parola: ")

app = Flask(__name__)
app.secret_key = "ilkblog"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "ilkblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

@app.route("/")
def index():
    articles = [{"id":"1","title":"Deneme1","content":"Deneme1 içerik"},
        {"id":"2","title":"Deneme2","content":"Deneme2 içerik"},
        {"id":"3","title":"Deneme3","content":"Deneme3 içerik"}]

    return render_template("index.html",articles = articles)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/articles")
def articles():

    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles"
    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()
        
        return render_template("articles.html",articles = articles)
    else:
        return render_template("articles.html")
    

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where author = %s"

    result = cursor.execute(sorgu,(session["username"],))

    if result >0:
        articles = cursor.fetchall()

        return render_template("dashboard.html",articles = articles)
    else:
        return render_template("dashboard.html")

#registerkayıtolma
@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        sorgu = "Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarıyla kayıt oldunuz","success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html",form = form)

#Login işlemi
@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password1 = form.password.data
        sorgu = "Select * From users where username = %s"
        cursor = mysql.connection.cursor()
        result = cursor.execute(sorgu,(username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password1,real_password):
                flash("Giriş başarıyla yapıldı","success")

                session["logged_in"] = True
                session["username"] = username
                
                return redirect(url_for("index"))
            else:
                flash("Kullanıcı adı veya parolanız yanlış!","danger")
                return redirect(url_for("login"))
        else:
            flash("Kullanıcı adı veya parolanız yanlış!","danger")
            return redirect(url_for("login"))
        
    else:
        return render_template("login.html",form = form)
#Detay Sayfası

@app.route("/article/<string:id>")
def article(id):

    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where id = %s"
    result = cursor.execute(sorgu,(id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article = article)
    else:
        return render_template("article.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/addarticle",methods=["GET","POST"])
def addArticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()

        sorgu = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Makaleniz başarıyla oluşturuldu!","success")
        return redirect(url_for("dashboard"))

        

    return render_template("addarticle.html",form = form)
#Makale Silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()

    sorgu = "Select * from articles where author = %s and id = %s"
    result = cursor.execute(sorgu,(session["username"],id))

    if result >0:
        sorgu2 = "Delete from articles where id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Makale veya yetkiniz yok","danger")
        return redirect(url_for("index"))
#Makale Güncelleme
@app.route("/edit/<string:id>",methods =["GET","POST"])
@login_required#Ulaşılması için üye girişi yapılması gereken yerlerde kullan :)
def update(id):
    
    if request.method == "GET":
        cursor = mysql.connection.cursor()

        sorgu = "Select * from articles where id = %s and author = %s"
        result = cursor.execute(sorgu,(id,session["username"]))
        if result == 0:
            flash("Makaleniz veya işleme yetkiniz yok","danger")
            return redirect(url_for("index"))

        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form = form)
    else:
        #POST REQUEST
        form = ArticleForm(request.form)

        newTitle = form.title.data
        newContent = form.content.data

        sorgu2 = "Update articles Set title = %s ,content = %s where id = %s"
        cursor = mysql.connection.cursor()

        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()

        flash("Makaleniz başarıyla güncellenmiştir.","info")
        return redirect(url_for("dashboard"))
        

#Makale Form
class ArticleForm(Form):
    title = StringField("Makalenizin Başlığı",validators=[validators.Length(min=5,max=100,message="5 ile 100 arasında karakter gir!")])
    content = TextAreaField("Makalenizin İçeriği",validators=[validators.Length(min=10,message="Minimum 10 karakter giriniz")])

#Arama url
@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method == "GET":
        flash("Hey!GOOGLE'lamak için bir şeyler yazman gerekli..","warning")
        return redirect(url_for("articles"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()

        sorgu = "Select * from articles where title like '%" + keyword +"%'"
        result = cursor.execute(sorgu)

        if result == 0:
            flash("Aranan kelimeyle alakalı makale bulunmamaktadır.","warning")
            return redirect(url_for("articles"))
        elif keyword == "":
            flash("Hey!GOOGLE'lamak için bir şeyler yazman gerekli..","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()

            return render_template("articles.html",articles  = articles)
if __name__ == "__main__":
    app.run(debug=True)
