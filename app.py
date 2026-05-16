import os
import mysql.connector
from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import config

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or 'dev-secret-change-in-prod'


def get_db_connection():
    try:
        return mysql.connector.connect(
            host=config.MYSQL_HOST,
            port=getattr(config, 'MYSQL_PORT', 3306),
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DB,
            connection_timeout=5,
        )
    except mysql.connector.Error as e:
        # Log a helpful message for debugging; avoid leaking password.
        app.logger.error(
            "Database connection failed: host=%s port=%s db=%s error=%r",
            getattr(config, 'MYSQL_HOST', None),
            getattr(config, 'MYSQL_PORT', 3306),
            getattr(config, 'MYSQL_DB', None),
            e,
        )
        raise



@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        confirm_password = request.form['confirm_password']
        password = request.form['password']

        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', 'error')
            return render_template('register.html')

        conn = get_db_connection()
        cur = conn.cursor(buffered=True)


        cur.execute("SELECT COUNT(*) FROM users WHERE email = %s", (email,))
        if cur.fetchone()[0] > 0:
            flash('Cet email est déjà utilisé.', 'error')
            cur.close()
            conn.close()
            return render_template('register.html')

        cur.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
        if cur.fetchone()[0] > 0:
            flash('Ce nom d\'utilisateur est déjà pris.', 'error')
            cur.close()
            conn.close()
            return render_template('register.html')

        try:
            hashed_password = generate_password_hash(password)
            cur.execute("INSERT INTO users (username, email, password, Action) VALUES (%s, %s, %s, %s)", (username, email, hashed_password, 'active'))
            conn.commit()
            session['user'] = username
            session['user_id'] = cur.lastrowid
            session['role'] = 'user'
            cur.close()
            conn.close()
            return redirect(url_for('users'))
        except Exception as e:
            flash('Erreur lors de l\'inscription. Veuillez réessayer.', 'error')
            cur.close()
            return render_template('register.html')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        cur = conn.cursor(buffered=True)
        cur.execute("SELECT * FROM users WHERE email = %s", [email])
        user = cur.fetchone()
        cur.close()
        if user and check_password_hash(user[3], password):
            session['user'] = user[1]
            session['user_id'] = user[0]
            session['role'] = user[5]
            return redirect(url_for('users'))
        else:
            flash('Email ou mot de passe incorrect.', 'error')
    return render_template('login.html')

@app.route('/users')
def users():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(buffered=True)

    try:
        # Seul l'admin voit toute la liste des utilisateurs
        if session.get('role') == 'admin':
            cur.execute("SELECT * FROM users")
            all_users = cur.fetchall()
        else:
            # Pour les non-admin: afficher uniquement l'utilisateur connecté
            cur.execute(
                "SELECT * FROM users WHERE id = %s",
                (session.get('user_id'),)
            )
            all_users = cur.fetchall()

        return render_template('users.html', users=all_users)
    finally:
        cur.close()
        conn.close()



@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('user_id', None)
    session.pop('role', None)
    return redirect(url_for('login'))

@app.route('/supprimer/<int:user_id>', methods=['POST'])
def supprimer(user_id):
    if 'user' not in session:
        flash('Veuillez vous connecter.', 'error')
        return redirect(url_for('login'))
    if session.get('role') != 'admin' and session.get('user_id') != user_id:
        flash('Action non autorisée.', 'error')
        return redirect(url_for('users'))

    conn = get_db_connection()
    cur = conn.cursor(buffered=True)

    try:
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        if session.get('user_id') == user_id:
            session.pop('user', None)
            session.pop('user_id', None)
            session.pop('role', None)
            flash('Compte supprimé avec succès.', 'success')
            return redirect(url_for('login'))
        flash('Utilisateur supprimé avec succès.', 'success')
    except Exception:
        conn.rollback()
        flash('Erreur lors de la suppression.', 'error')
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('users'))


# Routes pour les articles
@app.route('/articles')
def articles():
    if 'user' not in session:
        flash('Veuillez vous connecter.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(buffered=True)

    try:
        # Seul l'admin voit tous les articles. Les autres voient uniquement leurs articles.
        if session.get('role') == 'admin':
            cur.execute(
                """SELECT a.id, a.titre, a.contenu, a.date_creation, a.user_id, u.username
                   FROM articles a
                   JOIN users u ON a.user_id = u.id
                   ORDER BY a.date_creation DESC"""
            )
        else:
            cur.execute(
                """SELECT a.id, a.titre, a.contenu, a.date_creation, a.user_id, u.username
                   FROM articles a
                   JOIN users u ON a.user_id = u.id
                   WHERE a.user_id = %s
                   ORDER BY a.date_creation DESC""",
                (session.get('user_id'),)
            )

        all_articles = cur.fetchall()
        return render_template('articles.html', articles=all_articles)
    finally:
        cur.close()
        conn.close()



@app.route('/nouvel_article', methods=['GET', 'POST'])
def nouvel_article():
    if 'user' not in session:
        flash('Veuillez vous connecter.', 'error')
        return redirect(url_for('login'))
    if request.method == 'POST':
        titre = request.form['titre']
        contenu = request.form['contenu']
        user_id = session.get('user_id')

        conn = get_db_connection()
        cur = conn.cursor(buffered=True)
        try:
            cur.execute(
                "INSERT INTO articles (titre, contenu, user_id) VALUES (%s, %s, %s)",
                (titre, contenu, user_id)
            )
            conn.commit()
            flash('Article publié avec succès !', 'success')
            return redirect(url_for('articles'))
        except Exception:
            conn.rollback()
            flash('Erreur lors de la publication.', 'error')
            return render_template('nouvel_article.html')
        finally:
            cur.close()
            conn.close()
    return render_template('nouvel_article.html')


@app.route('/modifier_article/<int:article_id>', methods=['GET', 'POST'])
def modifier_article(article_id):
    if 'user' not in session:
        flash('Veuillez vous connecter.', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(buffered=True)
    try:
        cur.execute("SELECT * FROM articles WHERE id = %s", (article_id,))
        article = cur.fetchone()
        if not article:
            flash('Article non trouvé.', 'error')
            return redirect(url_for('articles'))
        # Vérifier les permissions
        if session.get('role') != 'admin' and session.get('user_id') != article[3]:
            flash('Action non autorisée.', 'error')
            return redirect(url_for('articles'))

        if request.method == 'POST':
            titre = request.form['titre']
            contenu = request.form['contenu']
            try:
                cur.execute(
                    "UPDATE articles SET titre=%s, contenu=%s WHERE id=%s",
                    (titre, contenu, article_id)
                )
                conn.commit()
                flash('Article modifié avec succès !', 'success')
                return redirect(url_for('articles'))
            except Exception:
                conn.rollback()
                flash('Erreur lors de la modification.', 'error')
                return render_template('modifier_article.html', article=article)

        return render_template('modifier_article.html', article=article)
    finally:
        cur.close()
        conn.close()


@app.route('/supprimer_article/<int:article_id>', methods=['POST'])
def supprimer_article(article_id):
    if 'user' not in session:
        flash('Veuillez vous connecter.', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(buffered=True)
    try:
        cur.execute("SELECT user_id FROM articles WHERE id = %s", (article_id,))
        result = cur.fetchone()
        if not result:
            flash('Article non trouvé.', 'error')
            return redirect(url_for('articles'))
        if session.get('role') != 'admin' and session.get('user_id') != result[0]:
            flash('Action non autorisée.', 'error')
            return redirect(url_for('articles'))

        try:
            cur.execute("DELETE FROM articles WHERE id = %s", (article_id,))
            conn.commit()
            flash('Article supprimé avec succès !', 'success')
        except Exception:
            conn.rollback()
            flash('Erreur lors de la suppression.', 'error')

        return redirect(url_for('articles'))
    finally:
        cur.close()
        conn.close()


@app.route('/modifier/<int:user_id>', methods=['GET', 'POST'])
def modifier(user_id):
    if 'user' not in session:
        flash('Veuillez vous connecter.', 'error')
        return redirect(url_for('login'))
    if session.get('role') != 'admin' and session.get('user_id') != user_id:
        flash('Action non autorisée.', 'error')
        return redirect(url_for('users'))
    conn = get_db_connection()
    cur = conn.cursor(buffered=True)
    try:
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form.get('password')

            cur.execute(
                "SELECT id FROM users WHERE (username = %s OR email = %s) AND id != %s",
                (username, email, user_id)
            )
            if cur.fetchone():
                flash("Nom d'utilisateur ou email déjà utilisé par un autre.", 'error')
                return redirect(url_for('modifier', user_id=user_id))

            update_sql = "UPDATE users SET username=%s, email=%s"
            params = [username, email]
            if password and password.strip():
                hashed_password = generate_password_hash(password)
                update_sql += ", password = %s"
                params.append(hashed_password)
            update_sql += " WHERE id = %s"
            params.append(user_id)

            cur.execute(update_sql, params)
            conn.commit()
            if session.get('user_id') == user_id:
                session['user'] = username
            flash('Compte mis à jour avec succès !', 'success')
            return redirect(url_for('users'))

        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if not user:
            flash('Utilisateur non trouvé.', 'error')
            return redirect(url_for('users'))
        return render_template('edit_user.html', user=user, user_id=user_id)
    except Exception:
        conn.rollback()
        flash('Erreur lors de la modification.', 'error')
        return redirect(url_for('users'))
    finally:
        cur.close()
        conn.close()


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

def ensure_default_admin():
    """Crée un admin par défaut si aucun admin n'existe."""
    admin_username = os.getenv('ADMIN_USERNAME', 'fawaz')
    admin_email = os.getenv('ADMIN_EMAIL', 'fawaz17@gmail.com')
    admin_password = os.getenv('ADMIN_PASSWORD', '17février')

    conn = get_db_connection()
    cur = conn.cursor(buffered=True)
    try:
        # Dans cette app, le rôle est stocké dans la colonne `Action` (et login utilise user[5])
        cur.execute("SELECT COUNT(*) FROM users WHERE Action = %s", ('admin',))
        if cur.fetchone()[0] > 0:
            return

        hashed_password = generate_password_hash(admin_password)
        cur.execute(
            "INSERT INTO users (username, email, password, Role) VALUES (%s, %s, %s, %s)",
            (admin_username, admin_email, hashed_password, 'admin'),
        )
        conn.commit()
        app.logger.info('Default admin created: %s', admin_email)
    except Exception as e:
        conn.rollback()
        app.logger.error('Failed to create default admin: %r', e)
        raise
    finally:
        cur.close()
        conn.close()


ensure_default_admin()

if __name__ == '__main__':
    app.run(debug=True)

