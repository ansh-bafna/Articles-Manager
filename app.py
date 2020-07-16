from flask import Flask,render_template,request,flash,redirect,url_for,session,logging
from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from logging.config import dictConfig
from functools import wraps
app=Flask(__name__)
app.secret_key='secret123'

#config MYSQL
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']=''
app.config['MYSQL_DB']='myflaskapp'
app.config['MYSQL_CURSORCLASS']='DictCursor'
#initialize mysql
mysql=MySQL(app)



@app.route('/')

def index():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/articles')
def articles():
     #create cursor
    cur=mysql.connection.cursor()
    result=cur.execute("SELECT * FROM articles")

    articles=cur.fetchall()
    if result>0:
        return render_template('articles.html',articles=articles)
    else: 
        msg="No Articles Found"   
        return render_template('articles.html',msg=msg) 

    cur.close()

@app.route('/article/<string:id>')
def article(id):
     #create cursor
    cur=mysql.connection.cursor()
    result=cur.execute("SELECT * FROM articles where id=%s", [id])

    article=cur.fetchone()
    return render_template('article.html',article=article)
  


class RegisterForm(Form):
    name=StringField('Name',[validators.Length(min=1,max=50)])
    username=StringField('Username',[validators.Length(min=4,max=25)])
    email=StringField('Email',[validators.Length(min=6,max=50)])
    password=PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm',message='Passwords do not match')
    ])
    confirm=PasswordField('Confirm Password')

@app.route('/register',methods=['GET','POST'])
def register():
    form=RegisterForm(request.form) 
    if request.method=='POST' and form.validate():
        name=form.name.data
        email=form.email.data
        username=form.username.data
        password=sha256_crypt.encrypt(str(form.password.data))

        #Create a cursor
        cur=mysql.connection.cursor()
        
        cur.execute("INSERT INTO users(name,email,username,password) VALUES(%s, %s, %s, %s)",(name,email,username,password))
        mysql.connection.commit()
        #close connection
        cur.close()

        flash('YOU ARE NOW REGISTERED AND CAN ACCESS YOUR ACCOUNT BY LOGGING IN','SUCCESS')


        return redirect(url_for('index'))
     
         
    return render_template('register.html',form=form)
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        username=request.form['username']
        password_candidate=request.form['password']

        #create cursor
        cur=mysql.connection.cursor()
        result=cur.execute("SELECT * FROM users WHERE username= %s", [username])

        if result>0:
            #get stored hash
            data=cur.fetchone()
            password=data['password']

            #compare passwords
            if sha256_crypt.verify(password_candidate,password):
                #passed
                session['logged_in']=True
                session['username']=username


                flash('You are now logged in','success')
                return redirect(url_for('dashboard'))
            else :
                error='Invalid login'
                return render_template('login.html',error=error)
            #close connection
            cur.close()    
        else :
            error='Username not found'
            return render_template('login.html',error=error)
        
    return render_template('login.html')
#Check if user logged in

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args,**kwargs)
        else:
            flash('Unauthorized,Please log in','danger')
            return redirect(url_for('login'))    
    return wrap


# how to access saved articles
@app.route('/saved_articles')
def saved_articles():

    #create cursor
    cur=mysql.connection.cursor()
    result=cur.execute("SELECT * FROM savearticle where author=%s",[session['username']] )
    articles=cur.fetchall()
    if result>0:
        return render_template('saved_articles.html',articles=articles)
    else: 
        msg="No Articles Found"   
        return render_template('saved_articles.html',msg=msg) 

    cur.close()
    

@app.route('/saved_article/<string:id>')
def show_saved_article(id):
     #create cursor
    cur=mysql.connection.cursor()
    result=cur.execute("SELECT * FROM savearticle where id=%s", [id])

    article=cur.fetchone()
    return render_template('show_saved_article.html',article=article)


#logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are logged out now ','success')
    return redirect(url_for('login'))



#dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    #create cursor
    cur=mysql.connection.cursor()
    result=cur.execute("SELECT * FROM articles WHERE author=%s", [session['username']])

    articles=cur.fetchall()
    if result>0:
        return render_template('dashboard.html',articles=articles)
    else: 
        msg="No Articles Found"   
        return render_template('dashboard.html',msg=msg) 

    cur.close()


class ArticleForm(Form):
    title=StringField('Title',[validators.Length(min=1,max=200)])
    body=TextAreaField('Body',[validators.Length(min=5)])


#add articles
@app.route('/add_article',methods=['GET','POST'])
@is_logged_in
def add_Article():
    form=ArticleForm(request.form)
    if request.method=='POST' and form.validate():
        title=form.title.data
        body=form.body.data

        #create cursor
        cur=mysql.connection.cursor()

        #Execute 
        cur.execute("INSERT INTO articles(title,body,author)VALUES(%s, %s, %s)",(title,body,session['username']))
        mysql.connection.commit()

        cur.close()

        flash("Article Created",'success')
        return redirect(url_for('dashboard'))


    return render_template('add_article.html',form=form) 


#saving articles
@app.route('/save_articles/<string:id>',methods=['GET','POST'])
@is_logged_in
def save_Article(id):
     #create cursor
    cur=mysql.connection.cursor()
    result=cur.execute("SELECT * FROM articles where id=%s", [id])
    article=cur.fetchone()
    
    form=ArticleForm(request.form)
    form.title.data=article['title']
    form.body.data=article['body']
    if request.method=='POST' and form.validate():
        title=request.form['title']
        body=request.form['body']
        

        #create cursor
        cur=mysql.connection.cursor()

        #Execute 
        cur.execute("INSERT INTO savearticle(title,body,author)VALUES(%s, %s, %s)",(title,body,session['username']))
        mysql.connection.commit()

        cur.close()

        flash("Article Saved",'success')
        return redirect(url_for('dashboard'))
    return render_template('save_articles.html',form=form)


#search for articles in dashboard by author or title
class SearchForm(Form):
    search=StringField('search',[validators.Length(min=1,max=200)])
    


@app.route('/search', methods=[ 'GET','POST'])
@is_logged_in
def search():
    form=SearchForm(request.form)
    if request.method == 'POST' and form.validate():
         
        
        #create cursor
        cur=mysql.connection.cursor()
        # search by author or title
        cur.execute("SELECT title, author,id FROM articles WHERE title LIKE %s OR author LIKE %s OR id LIKE %s", ['%'+request.form['search']+'%','%'+request.form['search']+'%','%'+request.form['search']+'%'])
        
        articles = cur.fetchall()
        mysql.connection.commit() 
        # all in the search box will return all the tuples
        if len(articles)==0:
          msg="No Articles Found"   
          return render_template('search.html',msg=msg)
        return render_template('search.html', articles=articles)
    return render_template('search.html')



#edit articles
@app.route('/edit_article/<string:id>',methods=['GET','POST'])
@is_logged_in
def edit_Article(id):
     #create cursor
    cur=mysql.connection.cursor()
    result=cur.execute("SELECT * FROM articles where id=%s", [id])
    article=cur.fetchone()

    form=ArticleForm(request.form)
    form.title.data=article['title']
    form.body.data=article['body']
    if request.method=='POST' and form.validate():
        title=request.form['title']
        body=request.form['body']

        #create cursor
        cur=mysql.connection.cursor()

        #Execute 
        cur.execute("UPDATE articles SET title=%s,body=%s WHERE id=%s",(title,body,id))
        mysql.connection.commit()

        cur.close()

        flash("Article Updated",'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_article.html',form=form)    


#for deleting articles  
@app.route('/delete_article/<string:id>',methods=['POST'])
@is_logged_in
def delete_article(id):
    #create cursor
    cur=mysql.connection.cursor()
    cur.execute("DELETE FROM articles WHERE id=%s",[id])
    mysql.connection.commit()
    cur.close()
    flash("Article Deleted",'success')
    return redirect(url_for('dashboard'))


    
          

    
if __name__=='__main__':
  app.run()