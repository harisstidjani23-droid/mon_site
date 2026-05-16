# TODO pour ajout actions Modifier/Supprimer + fix login

## Étapes à compléter:

### 1. Créer template edit_user.html ✅
   - Formulaire édition avec champs pré-remplis
   - Validation JS comme register.html

### 2. Modifier app.py ✅
   - Ajouter route /supprimer/<int:user_id> (POST, DELETE DB)
   - Ajouter route /modifier/<int:user_id> (GET form, POST update)
   - Ajouter vérif session dans /users
   - Optionnel: route debug pour DB

### 3. Modifier templates/users.html ✅
   - Form POST pour Supprimer avec confirm JS
   - Lien Modifier avec confirm JS

### 4. Tester localement
   - python app.py
   - Register, login, users, test actions

### 5. Fix live
   - Vérifier config.py creds XAMPP
   - Vérifier DB/table phpMyAdmin
   - Restart Apache/MySQL

**Progrès: 5/5 complété - Code implémenté ! Testez maintenant.**

## Commandes pour tester:
- Local: `cd c:/xampp/htdocs/mon_site && python app.py`
- Accédez: http://127.0.0.1:5000/register -> inscrivez-vous -> /login -> /users -> testez boutons
