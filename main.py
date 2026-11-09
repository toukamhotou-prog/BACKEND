import os
import shutil
import random
import string
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Query, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles  # <-- AJOUT POUR DISTRIBUER LES PDF
from sqlalchemy.orm import Session
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from passlib.context import CryptContext
from typing import Optional, List
import models
import schemas
from database import engine, get_db
from pydantic import BaseModel

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')[:72]
    return pwd_context.hash(password_bytes.decode('utf-8', errors='ignore'))

# Configuration SMTP de votre compte Gmail expéditeur
conf = ConnectionConfig(
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME","toukamhotou@gmail.com"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD","yuhukiimlecnjorf"),  # Clé d'application Google à 16 caractères
    MAIL_FROM=os.environ.get("MAIL_FROM","toukamhotou@gmail.com"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ÉpreuvesPro Backend", version="1.0")

# ==================== CONFIGURATION DES FICHIERS STATIQUES ====================
# Crée automatiquement le dossier s'il n'existe pas sur votre ordinateur
UPLOAD_DIR = "media/files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Permet au smartphone d'accéder aux fichiers via http://192.168.1...
app.mount("/media", StaticFiles(directory="media"), name="media")
# ==============================================================================

# Fonction asynchrone d'envoi d'e-mail réel
async def send_otp_email(email_to: str, otp_code: str, user_name: str):
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f6f8;">
        <div style="max-width: 500px; margin: 0 auto; background: #ffffff; padding: 24px; border-radius: 16px; border: 1px solid #e2e8f0;">
            <h2 style="color: #2563EB; margin-bottom: 8px;">ÉpreuvesPro</h2>
            <p style="color: #334155;">Bonjour <strong>{user_name}</strong>,</p>
            <p style="color: #475569;">Voici votre code de vérification à 6 chiffres pour valider votre inscription :</p>
            <div style="text-align: center; margin: 24px 0;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #0f172a; background: #eff6ff; padding: 12px 24px; border-radius: 12px; border: 1px solid #bfdbfe;">
                    {otp_code}
                </span>
            </div>
            <p style="color: #64748b; font-size: 13px;">Ce code est confidentiel. Ne le partagez avec personne.</p>
        </div>
    </div>
    """
    message = MessageSchema(
        subject="Code de vérification - ÉpreuvesPro",
        recipients=[email_to],
        body=html_content,
        subtype=MessageType.html
    )
    fm = FastMail(conf)
    await fm.send_message(message)

@app.post("/api/register", status_code=status.HTTP_201_CREATED)
async def register(user_data: schemas.UserRegister, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        print(f"Tentative d'inscription pour : {user_data.email}")
        existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
        
        otp = ''.join(random.choices(string.digits, k=6))
        
        if existing_user:
            if existing_user.is_verified:
                raise HTTPException(status_code=400, detail="Un compte vérifié existe déjà.")
            existing_user.full_name = user_data.full_name
            existing_user.password_hash = hash_password(user_data.password)
            existing_user.study_level = user_data.study_level
            existing_user.otp_code = otp
            db.commit()
        else:
            new_user = models.User(
                full_name=user_data.full_name,
                email=user_data.email,
                password_hash=hash_password(user_data.password),
                study_level=user_data.study_level,
                otp_code=otp,
                is_verified=False
            )
            db.add(new_user)
            db.commit()
        print("Utilisateur enregistré en base. Envoi du mail en arrière-plan...")
        background_tasks.add_task(send_otp_email, user_data.email, otp, user_data.full_name)
        return {
            "success": True,
            "message": f"Code de vérification envoyé à {user_data.email}",
            "email": user_data.email
        }
    except Exception as e:
        print(f"ERREUR BACKEND : {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/verify-otp")
def verify_otp(data: schemas.VerifyOTP, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    
    if user.otp_code != data.otp_code:
        raise HTTPException(status_code=400, detail="Code de vérification incorrect.")
    
    user.is_verified = True
    user.otp_code = None
    db.commit()
    
    return {
        "success": True,
        "message": "Compte vérifié avec succès !"
    }

@app.post("/api/login")
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="E-mail ou mot de passe incorrect.")
    
    password_bytes = credentials.password.encode('utf-8')[:72]
    if not pwd_context.verify(password_bytes.decode('utf-8', errors='ignore'), user.password_hash):
        raise HTTPException(status_code=400, detail="E-mail ou mot de passe incorrect.")
    
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Veuillez d'abord valider votre compte avec le code OTP reçu par e-mail.")
    
    return {
        "success": True,
        "message": "Connexion réussie !",
        "full_name": user.full_name,
        "email": user.email,
        "study_level": user.study_level
    }

@app.get('/api/user-profile')
def get_user_profile(email: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return {
        "full_name": user.full_name,
        "email": user.email,
        "study_level": user.study_level
    }

# ==================== ROUTE DE DÉPÔT CORRIGÉE POUR LE BINAIRE ====================
@app.post("/api/epreuves", status_code=status.HTTP_201_CREATED)
async def create_epreuve(
    email: str = Query(...),
    title: str = Form(...),
    subject: str = Form(...),
    school: str = Form(...),
    date: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    
    # Génération d'un nom de fichier unique et sécurisé
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "pdf"
    unique_filename = f"epreuve_{user.id}_{random.randint(1000, 9999)}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Écriture du fichier binaire sur le stockage du serveur
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Création du chemin d'accès relatif pour la base de données
    db_file_uri = f"/{file_path}"

    new_epreuve = models.Epreuves(
        title=title,
        subject=subject,
        school=school,
        study_level=user.study_level,
        date=date,
        file_uri=db_file_uri,
        downloads=0,
        user_id=user.id
    )
    db.add(new_epreuve)
    db.commit()
    db.refresh(new_epreuve)
    return {"success": True, "message": "Épreuve publiée avec succès !", "id": new_epreuve.id}
# ==============================================================================

@app.get("/api/epreuves", response_model=List[schemas.EpreuvesResponse])
def get_epreuves(
    email: str = Query(...),
    search: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
        
    query = db.query(models.Epreuves).filter(models.Epreuves.study_level == user.study_level)
    
    if subject and subject != "Toutes":
        query = query.filter(models.Epreuves.subject == subject)
        
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (models.Epreuves.title.ilike(search_filter)) | 
            (models.Epreuves.date.ilike(search_filter)) |
            (models.Epreuves.school.ilike(search_filter))
        )
        
    return query.all()

@app.post("/api/epreuves/{epreuve_id}/download")
def increment_download(epreuve_id: int, db: Session = Depends(get_db)):
    epreuve = db.query(models.Epreuves).filter(models.Epreuves.id == epreuve_id).first()
    if not epreuve:
        raise HTTPException(status_code=404, detail="Épreuve introuvable.")
    epreuve.downloads += 1
    db.commit()
    return {"success": True, "downloads": epreuve.downloads}


@app.get("/api/subjects", response_model=List[str])
def get_subjects(email:str=Query(...), db:Session=Depends(get_db)):
    user=db.query(models.User).filter(models.User.email== email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    user_level_exams= db.query(models.Epreuves.subject).filter(models.Epreuves.study_level == user.study_level).distinct().all()

    subjects_list=['Toutes'] + [exam[0] for exam in user_level_exams if exam[0]]
    return subjects_list

@app.get("/api/stats/impact")
def get_user_impact(email: str = Query(...), db: Session = Depends(get_db)):
    """
    Calcule et retourne les statistiques d'impact de l'utilisateur :
    - Épreuves partagées et score (2 pts par épreuve)
    - Total des téléchargements et historique détaillé (étudiant, épreuve, date, heure)
    - Statut des badges (Contributeur Actif > 100, Top Réviseur > 15, Expert Scientifique en maintenance)
    """
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    
    # 1. Récupérer les épreuves postées par cet utilisateur
    # Note: Assurez-vous que votre modèle Epreuves possède un champ 'user_id' ou 'email' lié à l'auteur
    user_exams = db.query(models.Epreuves).filter(models.Epreuves.user_id == user.id).all() # ou .filter(models.Epreuves.user_id == user.id)
    
    shared_exams_count = len(user_exams)
    
    # 2. Score d'impact : 2 points par épreuve déposée
    impact_score = shared_exams_count * 2
    
    # 3. Calculer les téléchargements et récupérer l'historique
    total_downloads = 0
    downloads_history = []
    
    for exam in user_exams:
        total_downloads += getattr(exam, 'downloads', 0)
        
        # Si vous possédez une table de traçabilité des téléchargements (ex: DownloadRecord), 
        # vous pouvez l'interroger ici. Exemple basique :
        # records = db.query(models.DownloadRecord).filter(models.DownloadRecord.epreuve_id == exam.id).all()
        # Pour l'exemple, si vous stockez l'historique, adaptez selon votre modèle :
        downloads_history.append({
            "student_name": "Étudiant de la communauté",
            "exam_title": exam.title,
            "date": "Récemment",
            "time": ""
        })

    return {
        "score": impact_score,
        "shared_exams": shared_exams_count,
        "total_downloads": total_downloads,
        "downloads_history": downloads_history,
        "badges": {
            "active_contributor_unlocked": shared_exams_count > 100,  # Débloqué si > 100 épreuves
            "top_reviewer_unlocked": total_downloads > 15,            # Débloqué si > 15 téléchargements
            "expert_scientifique_status": "maintenance"
        }
    }

@app.get("/api/user/downloads")
def get_user_downloads(email: str = Query(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    
    # Ici, vous pouvez lier aux téléchargements réels de l'utilisateur. 
    # Pour l'exemple, on retourne les épreuves avec des dates formatées pour le filtre par jour.
    user_downloads = db.query(models.Epreuves).limit(10).all()
    
    result = []
    for exam in user_downloads:
        result.append({
            "id": exam.id,
            "title": exam.title,
            "subject": exam.subject,
            "school": exam.school,
            "date": getattr(exam, 'date', "Aujourd'hui"), # Format attendu pour le filtre (ex: "2026-11-08" ou "Aujourd'hui")
            "file_uri": exam.file_uri
        })
    return result

# Route pour modifier le nom ou le mot de passe

class UserUpdate(BaseModel):
    email: str
    full_name: Optional[str] = None
    password: Optional[str] = None

@app.put("/api/user/update")
def update_user_profile(data: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    
    if data.full_name:
        user.full_name = data.full_name
    if data.password:
        user.password_hash = hash_password(data.password)
        
    db.commit()
    return {"success": True, "message": "Profil mis à jour avec succès !", "full_name": user.full_name}



