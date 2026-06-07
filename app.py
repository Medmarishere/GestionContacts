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
    
    # --- AJOUT POUR LA RECHERCHE (US 1.4) ---
    # On récupère le terme tapé dans la barre de recherche (si vide, on renvoie une chaîne vide)
    terme_recherche = request.args.get('q', '').strip()
    
    if terme_recherche:
        # Si une recherche est faite, on filtre par nom OU par téléphone
        contacts = conn.execute(
            'SELECT * FROM contacts WHERE nom LIKE ? OR tel LIKE ? ORDER BY nom ASC', 
            (f'%{terme_recherche}%', f'%{terme_recherche}%')
        ).fetchall()
    else:
        # Sinon, on affiche tout
        contacts = conn.execute('SELECT * FROM contacts ORDER BY nom ASC').fetchall()
    # ----------------------------------------

    conn.close()
    
    # On passe le "terme_recherche" au template HTML pour le garder affiché dans la barre
    return render_template('index.html', contacts=contacts, session=session, recherche=terme_recherche)

@app.route('/ajouter', methods=['POST'])
def ajouter():
    if session.get('role') != 'admin':
        flash("Action non autorisée.", "error")
        return redirect(url_for('index'))
    
    nom = request.form['nom'].strip()
    tel = request.form['tel'].strip()
    email = request.form['email'].strip()
    
    if not re.match(r"^[A-Za-zÀ-ÿ\s\-]{2,}$", nom) or not re.match(r"^(?:\+|0)[0-9][0-9\s\-]{6,14}$", tel) or not re.match(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$", email):
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