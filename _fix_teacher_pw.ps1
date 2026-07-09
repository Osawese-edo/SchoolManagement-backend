$d = "C:\Users\HP\Software-Dev\CLIENT JOB\SCHOOL PORTAL\DESTINED\backend"
& "$d\venv\Scripts\python" -c @"
import sys
sys.path.insert(0, r'$d')
from app.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

db = SessionLocal()
t = db.query(User).filter(User.role == 'teacher').first()
print(f'Teacher: {t.email}')

new_pw = 'teacher123'
t.hashed_password = get_password_hash(new_pw)
db.commit()
print(f'Password reset to: {new_pw}')
"@
