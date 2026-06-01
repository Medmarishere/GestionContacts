""" # Fichier : ContactApp/app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import re
import csv
import os

app = Flask(__name__)
app.secret_key = "cle_secrete_tres_complexe" # Nécessaire pour les sessions et les messages flash

# ==========================================
# 1. Gestion de la Base de Données
# ==========================================
def get_db_connection():
    conn = sqlite3.connect('contacts.db')
    conn.row_factory = sqlite3.Row # Permet d'accéder aux colonnes par leur nom
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE,
            tel TEXT,
            email TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialiser la base au démarrage
init_db()

class AddressBook:

    def ajouter_contact(self, nom, tel, email):
        # 1. Vérification manuelle de l'email (très important si votre ancienne base existe déjà)
        self.cursor.execute("SELECT id FROM contacts WHERE email = ?", (email,))
        if self.cursor.fetchone() is not None:
            return "erreur_email" # L'email existe déjà !

        # 2. Tentative d'insertion
        try:
            self.cursor.execute(
                "INSERT INTO contacts (nom, tel, email) VALUES (?, ?, ?)", 
                (nom, tel, email)
            )
            self.conn.commit()
            return "succes"
        except sqlite3.IntegrityError:
            # Si le nom existe déjà (grâce à la contrainte UNIQUE)
            return "erreur_nom"

    def supprimer_contact(self, nom):
        self.cursor.execute("DELETE FROM contacts WHERE nom = ?", (nom,))
        self.conn.commit()

    def obtenir_contacts_tries(self):
        self.cursor.execute("SELECT nom, tel, email FROM contacts ORDER BY nom ASC")
        return self.cursor.fetchall()

    def obtenir_un_contact(self, nom):
        self.cursor.execute("SELECT tel, email FROM contacts WHERE nom = ?", (nom,))
        return self.cursor.fetchone()

    def exporter_vers_csv(self, nom_fichier="mes_contacts.csv"):
        contacts = self.obtenir_contacts_tries()
        try:
            with open(nom_fichier, mode='w', newline='', encoding='utf-8') as fichier_csv:
                writer = csv.writer(fichier_csv)
                writer.writerow(["Nom", "Téléphone", "Email"])
                writer.writerows(contacts)
            return True
        except Exception as e:
            print(f"Erreur lors de l'exportation : {e}")
            return False

# ==========================================
# 2. Routes (Les pages Web)
# ==========================================

# --- PAGE DE CONNEXION ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        utilisateurs_autorises = {"admin": "1234", "Mohammed": "admin"}
        
        if username in utilisateurs_autorises and utilisateurs_autorises[username] == password:
            session['user'] = username # On enregistre l'utilisateur dans la session
            return redirect(url_for('index'))
        else:
            flash("Identifiants incorrects !", "error")
            
    return render_template('login.html')

# --- DÉCONNEXION ---
@app.route('/logout')
def logout():
    session.pop('user', None) # On supprime la session
    return redirect(url_for('login'))

# --- CARNET D'ADRESSES  ---
@app.route('/index', methods=['GET'])
def index():
    if 'user' not in session:
        return redirect(url_for('login')) # Bloque l'accès si non connecté
    
    conn = get_db_connection()
    contacts = conn.execute('SELECT * FROM contacts ORDER BY nom ASC').fetchall()
    conn.close()
    
    return render_template('index.html', contacts=contacts, user=session['user'])

# --- AJOUTER UN CONTACT ---
@app.route('/ajouter', methods=['POST'])
def ajouter():
    if 'user' not in session: return redirect(url_for('login'))
    
    nom = request.form['nom'].strip()
    tel = request.form['tel'].strip()
    email = request.form['email'].strip()
    
    # Validation Regex
    if not re.match(r"^[A-Za-zÀ-ÿ\s\-]{2,}$", nom):
        flash("Nom invalide.", "error")
        return redirect(url_for('index'))
    if not re.match(r"^\+?[\d\s\-]{8,15}$", tel):
        flash("Téléphone invalide.", "error")
        return redirect(url_for('index'))
    if not re.match(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$", email):
        flash("Email invalide.", "error")
        return redirect(url_for('index'))

    # Insertion SQL
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO contacts (nom, tel, email) VALUES (?, ?, ?)", (nom, tel, email))
        conn.commit()
        flash("Contact ajouté avec succès !", "success")
    except sqlite3.IntegrityError:
        flash("Ce nom existe déjà.", "error")
    finally:
        conn.close()
        
    return redirect(url_for('index'))

# --- SUPPRIMER UN CONTACT ---
@app.route('/supprimer/<nom>')
def supprimer(nom):
    if 'user' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    conn.execute("DELETE FROM contacts WHERE nom = ?", (nom,))
    conn.commit()
    conn.close()
    
    flash(f"Contact {nom} supprimé.", "success")
    return redirect(url_for('index'))

# --- EXPORTER CSV ---
@app.route('/exporter')
def exporter():
    if 'user' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    contacts = conn.execute('SELECT nom, tel, email FROM contacts ORDER BY nom ASC').fetchall()
    conn.close()
    
    chemin_fichier = "export_contacts.csv"
    with open(chemin_fichier, mode='w', newline='', encoding='utf-8') as fichier_csv:
        writer = csv.writer(fichier_csv)
        writer.writerow(["Nom", "Téléphone", "Email"])
        for c in contacts:
            writer.writerow([c['nom'], c['tel'], c['email']])
            
    # Flask envoie le fichier directement au navigateur pour le téléchargement
    return send_file(chemin_fichier, as_attachment=True)

if __name__ == '__main__':
    # Lance le serveur local (debug=True permet de recharger la page automatiquement quand on modifie le code)
    app.run(debug=True) """


""" # Fichier : ContactApp/app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import re
import csv
import io  # Requis pour traiter le flux de fichier importé

app = Flask(__name__)
app.secret_key = "cle_secrete_tres_complexe" 

# ==========================================
# 1. Gestion de la Base de Données
# ==========================================
def get_db_connection():
    conn = sqlite3.connect('contacts.db')
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE,
            tel TEXT,
            email TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. Routes (Les pages Web)
# ==========================================

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        utilisateurs_autorises = {"admin": "1234", "Mohammed": "admin"}
        
        if username in utilisateurs_autorises and utilisateurs_autorises[username] == password:
            session['user'] = username 
            return redirect(url_for('index'))
        else:
            flash("Identifiants incorrects !", "error")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None) 
    return redirect(url_for('login'))

@app.route('/index', methods=['GET'])
def index():
    if 'user' not in session:
        return redirect(url_for('login')) 
    
    conn = get_db_connection()
    contacts = conn.execute('SELECT * FROM contacts ORDER BY nom ASC').fetchall()
    conn.close()
    
    return render_template('index.html', contacts=contacts, user=session['user'])

@app.route('/ajouter', methods=['POST'])
def ajouter():
    if 'user' not in session: return redirect(url_for('login'))
    
    nom = request.form['nom'].strip()
    tel = request.form['tel'].strip()
    email = request.form['email'].strip()
    
    if not re.match(r"^[A-Za-zÀ-ÿ\s\-]{2,}$", nom):
        flash("Nom invalide (min. 2 lettres).", "error")
        return redirect(url_for('index'))
    if not re.match(r"^\+?[\d\s\-]{8,15}$", tel):
        flash("Téléphone invalide (8 à 15 chiffres).", "error")
        return redirect(url_for('index'))
    if not re.match(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$", email):
        flash("Format d'email invalide.", "error")
        return redirect(url_for('index'))

    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO contacts (nom, tel, email) VALUES (?, ?, ?)", (nom, tel, email))
        conn.commit()
        flash("Contact ajouté avec succès !", "success")
    except sqlite3.IntegrityError:
        flash("Ce nom ou cet email existe déjà.", "error")
    finally:
        conn.close()
        
    return redirect(url_for('index'))

# --- NOUVELLE ROUTE : IMPORTER DU DATA FILE (CSV) ---
@app.route('/importer', methods=['POST'])
def importer():
    if 'user' not in session: return redirect(url_for('login'))
    
    # 1. On récupère le fichier envoyé par le formulaire
    if 'file' not in request.files:
        flash("Aucun fichier trouvé.", "error")
        return redirect(url_for('index'))
        
    file = request.files['file']
    
    if file.filename == '':
        flash("Aucun fichier sélectionné.", "error")
        return redirect(url_for('index'))
        
    # 2. Sécurité : On s'assure que c'est bien un fichier .csv
    if file and file.filename.endswith('.csv'):
        try:
            # Transformation du fichier binaire en texte lisible par le module CSV
            stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
            lecteur_csv = csv.reader(stream)
            
            # On ignore la première ligne si elle contient les entêtes (Nom, Téléphone, Email)
            premiere_ligne = next(lecteur_csv, None)
            
            conn = get_db_connection()
            ajouts_reussis = 0
            erreurs = 0
            
            for ligne in lecteur_csv:
                # Protection si une ligne est incomplète
                if len(ligne) < 3:
                    continue
                
                nom, tel, email = ligne[0].strip(), ligne[1].strip(), ligne[2].strip()
                
                # Validation stricte par Regex (comme pour l'ajout unitaire)
                if (re.match(r"^[A-Za-zÀ-ÿ\s\-]{2,}$", nom) and 
                    re.match(r"^\+?[\d\s\-]{8,15}$", tel) and 
                    re.match(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$", email)):
                    
                    try:
                        conn.execute("INSERT INTO contacts (nom, tel, email) VALUES (?, ?, ?)", (nom, tel, email))
                        ajouts_reussis += 1
                    except sqlite3.IntegrityError:
                        erreurs += 1 # Gère les doublons silencieusement
                else:
                    erreurs += 1 # Données mal formatées dans le fichier
            
            conn.commit()
            conn.close()
            
            if ajouts_reussis > 0:
                flash(f"Succès ! {ajouts_reussis} contacts ont été importés. ({erreurs} ignorés car doublons ou invalides)", "success")
            else:
                flash(f"Aucun contact importé. Vérifiez si les contacts existent déjà ou s'ils respectent les formats.", "error")
                
        except Exception as e:
            flash(f"Erreur lors de la lecture du fichier : {e}", "error")
    else:
        flash("Format invalide. Veuillez fournir un fichier au format .csv", "error")
        
    return redirect(url_for('index'))

@app.route('/supprimer/<nom>')
def supprimer(nom):
    if 'user' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    conn.execute("DELETE FROM contacts WHERE nom = ?", (nom,))
    conn.commit()
    conn.close()
    
    flash(f"Contact {nom} supprimé.", "success")
    return redirect(url_for('index'))

@app.route('/exporter')
def exporter():
    if 'user' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    contacts = conn.execute('SELECT nom, tel, email FROM contacts ORDER BY nom ASC').fetchall()
    conn.close()
    
    chemin_fichier = "export_contacts.csv"
    with open(chemin_fichier, mode='w', newline='', encoding='utf-8') as fichier_csv:
        writer = csv.writer(fichier_csv)
        writer.writerow(["Nom", "Téléphone", "Email"])
        for c in contacts:
            writer.writerow([c['nom'], c['tel'], c['email']])
            
    return send_file(chemin_fichier, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True) """


""" # Fichier : ContactApp/app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import re
import csv
import io

app = Flask(__name__)
app.secret_key = "cle_secrete_tres_complexe" 

# ==========================================
# 1. Gestion de la Base de Données
# ==========================================
def get_db_connection():
    conn = sqlite3.connect('contacts.db')
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE,
            tel TEXT,
            email TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. Routes (Les pages Web)
# ==========================================

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        utilisateurs_autorises = {"admin": "1234", "Mohammed": "admin"}
        
        if username in utilisateurs_autorises and utilisateurs_autorises[username] == password:
            session['user'] = username 
            session['role'] = 'admin' # <-- Rôle Administrateur
            return redirect(url_for('index'))
        else:
            flash("Identifiants incorrects !", "error")
            
    return render_template('login.html')

# --- NOUVELLE ROUTE : CONNEXION INVITÉ ---
@app.route('/guest')
def guest_login():
    session['user'] = 'Visiteur'
    session['role'] = 'guest' # <-- Rôle Invité
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear() # Vide toute la session (utilisateur + rôle)
    return redirect(url_for('login'))

@app.route('/index', methods=['GET'])
def index():
    if 'user' not in session:
        return redirect(url_for('login')) 
    
    conn = get_db_connection()
    contacts = conn.execute('SELECT * FROM contacts ORDER BY nom ASC').fetchall()
    conn.close()
    
    # On passe toute la session au template pour vérifier le rôle
    return render_template('index.html', contacts=contacts, session=session)

@app.route('/ajouter', methods=['POST'])
def ajouter():
    # Sécurité : On bloque si ce n'est pas un admin
    if session.get('role') != 'admin':
        flash("Action non autorisée. Réservé aux administrateurs.", "error")
        return redirect(url_for('index'))
    
    nom = request.form['nom'].strip()
    tel = request.form['tel'].strip()
    email = request.form['email'].strip()
    
    if not re.match(r"^[A-Za-zÀ-ÿ\s\-]{2,}$", nom) or not re.match(r"^\+?[\d\s\-]{8,15}$", tel) or not re.match(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$", email):
        flash("Format des données invalide.", "error")
        return redirect(url_for('index'))

    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO contacts (nom, tel, email) VALUES (?, ?, ?)", (nom, tel, email))
        conn.commit()
        flash("Contact ajouté avec succès !", "success")
    except sqlite3.IntegrityError:
        flash("Ce nom ou cet email existe déjà.", "error")
    finally:
        conn.close()
        
    return redirect(url_for('index'))

@app.route('/importer', methods=['POST'])
def importer():
    # Sécurité : Admin uniquement
    if session.get('role') != 'admin':
        flash("Action non autorisée.", "error")
        return redirect(url_for('index'))
    
    if 'file' not in request.files: return redirect(url_for('index'))
    file = request.files['file']
    
    if file and file.filename.endswith('.csv'):
        try:
            stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
            lecteur_csv = csv.reader(stream)
            next(lecteur_csv, None)
            
            conn = get_db_connection()
            ajouts_reussis, erreurs = 0, 0
            
            for ligne in lecteur_csv:
                if len(ligne) < 3: continue
                nom, tel, email = ligne[0].strip(), ligne[1].strip(), ligne[2].strip()
                try:
                    conn.execute("INSERT INTO contacts (nom, tel, email) VALUES (?, ?, ?)", (nom, tel, email))
                    ajouts_reussis += 1
                except sqlite3.IntegrityError:
                    erreurs += 1 
            conn.commit()
            conn.close()
            flash(f"Succès ! {ajouts_reussis} importés. ({erreurs} ignorés)", "success")
        except Exception as e:
            flash(f"Erreur de lecture : {e}", "error")
    else:
        flash("Fichier CSV requis.", "error")
        
    return redirect(url_for('index'))

@app.route('/supprimer/<nom>')
def supprimer(nom):
    # Sécurité : Admin uniquement
    if session.get('role') != 'admin':
        flash("Action non autorisée.", "error")
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    conn.execute("DELETE FROM contacts WHERE nom = ?", (nom,))
    conn.commit()
    conn.close()
    
    flash(f"Contact {nom} supprimé.", "success")
    return redirect(url_for('index'))

@app.route('/exporter')
def exporter():
    # Sécurité : Admin uniquement (Modifiez si vous voulez que les invités puissent exporter)
    if session.get('role') != 'admin':
        flash("Seuls les administrateurs peuvent exporter la base.", "error")
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    contacts = conn.execute('SELECT nom, tel, email FROM contacts ORDER BY nom ASC').fetchall()
    conn.close()
    
    chemin_fichier = "export_contacts.csv"
    with open(chemin_fichier, mode='w', newline='', encoding='utf-8') as fichier_csv:
        writer = csv.writer(fichier_csv)
        writer.writerow(["Nom", "Téléphone", "Email"])
        for c in contacts:
            writer.writerow([c['nom'], c['tel'], c['email']])
            
    return send_file(chemin_fichier, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True) """



# Fichier : ContactApp/app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import re
import csv
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = "cle_secrete_tres_complexe" 

# ==========================================
# 1. Gestion de la Base de Données
# ==========================================
def get_db_connection():
    conn = sqlite3.connect('contacts.db')
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE,
            tel TEXT,
            email TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. Routes (Les pages Web)
# ==========================================

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        utilisateurs_autorises = {"admin": "1234", "Mohammed": "admin"}
        
        if username in utilisateurs_autorises and utilisateurs_autorises[username] == password:
            session['user'] = username 
            session['role'] = 'admin'
            return redirect(url_for('index'))
        else:
            flash("Identifiants incorrects !", "error")
            
    return render_template('login.html')

@app.route('/guest')
def guest_login():
    session['user'] = 'Visiteur'
    session['role'] = 'guest'
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/index', methods=['GET'])
def index():
    if 'user' not in session:
        return redirect(url_for('login')) 
    
    conn = get_db_connection()
    contacts = conn.execute('SELECT * FROM contacts ORDER BY nom ASC').fetchall()
    conn.close()
    
    return render_template('index.html', contacts=contacts, session=session)

@app.route('/ajouter', methods=['POST'])
def ajouter():
    if session.get('role') != 'admin':
        flash("Action non autorisée.", "error")
        return redirect(url_for('index'))
    
    nom = request.form['nom'].strip()
    tel = request.form['tel'].strip()
    email = request.form['email'].strip()
    
    if not re.match(r"^[A-Za-zÀ-ÿ\s\-]{2,}$", nom) or not re.match(r"^\+?[\d\s\-]{8,15}$", tel) or not re.match(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$", email):
        flash("Format des données invalide.", "error")
        return redirect(url_for('index'))

    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO contacts (nom, tel, email) VALUES (?, ?, ?)", (nom, tel, email))
        conn.commit()
        flash("Contact ajouté avec succès !", "success")
    except sqlite3.IntegrityError:
        flash("Ce nom ou cet email existe déjà.", "error")
    finally:
        conn.close()
        
    return redirect(url_for('index'))

@app.route('/importer', methods=['POST'])
def importer():
    if session.get('role') != 'admin':
        flash("Action non autorisée.", "error")
        return redirect(url_for('index'))
    
    if 'file' not in request.files: return redirect(url_for('index'))
    file = request.files['file']
    
    if file and file.filename.endswith('.csv'):
        try:
            stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
            lecteur_csv = csv.reader(stream)
            next(lecteur_csv, None)
            
            conn = get_db_connection()
            ajouts_reussis, erreurs = 0, 0
            
            for ligne in lecteur_csv:
                if len(ligne) < 3: continue
                nom, tel, email = ligne[0].strip(), ligne[1].strip(), ligne[2].strip()
                try:
                    conn.execute("INSERT INTO contacts (nom, tel, email) VALUES (?, ?, ?)", (nom, tel, email))
                    ajouts_reussis += 1
                except sqlite3.IntegrityError:
                    erreurs += 1 
            conn.commit()
            conn.close()
            flash(f"Succès ! {ajouts_reussis} importés. ({erreurs} ignorés)", "success")
        except Exception as e:
            flash(f"Erreur de lecture : {e}", "error")
    else:
        flash("Fichier CSV requis.", "error")
        
    return redirect(url_for('index'))

@app.route('/supprimer/<nom>')
def supprimer(nom):
    if session.get('role') != 'admin':
        flash("Action non autorisée.", "error")
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    conn.execute("DELETE FROM contacts WHERE nom = ?", (nom,))
    conn.commit()
    conn.close()
    
    flash(f"Contact {nom} supprimé.", "success")
    return redirect(url_for('index'))

@app.route('/exporter')
def exporter():
    if session.get('role') != 'admin':
        flash("Action non autorisée.", "error")
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    contacts = conn.execute('SELECT nom, tel, email FROM contacts ORDER BY nom ASC').fetchall()
    conn.close()
    
    chemin_fichier = "export_contacts.csv"
    with open(chemin_fichier, mode='w', newline='', encoding='utf-8') as fichier_csv:
        writer = csv.writer(fichier_csv)
        writer.writerow(["Nom", "Téléphone", "Email"])
        for c in contacts:
            writer.writerow([c['nom'], c['tel'], c['email']])
            
    return send_file(chemin_fichier, as_attachment=True)

# ==========================================
# 3. NOUVELLES ROUTES : COMMUNICATION
# ==========================================

@app.route('/envoyer_email/<nom>/<email>')
def envoyer_email(nom, email):
    if session.get('role') != 'admin':
        flash("Action non autorisée.", "error")
        return redirect(url_for('index'))

    # /!\ ATTENTION : Pour que cela fonctionne, vous devez configurer un vrai email
    # Si vous utilisez Gmail, il faut générer un "Mot de passe d'application"
    expediteur = "shineandrisenow@gmail.com" 
    mot_de_passe = "pqyp fvqh ucee chcl" 

    msg = MIMEMultipart()
    msg['From'] = expediteur
    msg['To'] = email
    msg['Subject'] = "Confirmation de rendez-vous médical"
    
    corps_message = f"""Bonjour {nom},

Ceci est un message automatique du cabinet.
Nous vous confirmons votre rendez-vous. En cas d'empêchement, merci de nous prévenir 24h à l'avance.

Cordialement,
Le Cabinet Médical"""
    
    msg.attach(MIMEText(corps_message, 'plain', 'utf-8'))

    try:
        # Connexion au serveur de messagerie (exemple pour Gmail)
        serveur = smtplib.SMTP('smtp.gmail.com', 587)
        serveur.starttls() # Sécurise la connexion
        serveur.login(expediteur, mot_de_passe)
        serveur.send_message(msg)
        serveur.quit()
        
        flash(f"Email de confirmation envoyé avec succès à {nom}.", "success")
    except Exception as e:
        # Si vous n'avez pas configuré les identifiants, cette erreur s'affichera
        flash(f"L'email n'a pas pu être envoyé (Vérifiez la configuration SMTP). Erreur: {e}", "error")

    return redirect(url_for('index'))
@app.route('/envoyer_whatsapp/<nom>/<tel>')
def envoyer_whatsapp(nom, tel):
    # Sécurité : On s'assure que c'est un admin
    if session.get('role') != 'admin':
        flash("Action non autorisée.", "error")
        return redirect(url_for('index'))

    # 1. Nettoyer le numéro de téléphone (ne garder que les chiffres)
    numero_propre = re.sub(r'[^\d]', '', tel)
    
    # 2. Le message que vous voulez envoyer
    message = f"Bonjour {nom},\n\nNous vous confirmons votre rendez-vous. En cas d'empêchement, merci de nous prévenir 24h à l'avance.\n\nCordialement,\nLe Cabinet Médical"
    
    # 3. Encoder le message pour l'URL (remplace les espaces, retours à la ligne, etc.)
    message_encode = urllib.parse.quote(message)

    # 4. Créer le lien wa.me officiel de WhatsApp
    lien_whatsapp = f"https://wa.me/{numero_propre}?text={message_encode}"

    # 5. Rediriger vers WhatsApp
    return redirect(lien_whatsapp)
if __name__ == '__main__':
    app.run(debug=True)