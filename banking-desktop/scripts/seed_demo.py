import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import init_db, get_db
from app.db.models import User, Account, AccountType, Transaction, TransactionType, UploadedDocument, DocumentChunk
from app.security.hashing import hash_password, hash_pin
from app.services.account_service import open_account
from app.services.pin_service import set_pin

def seed():
    init_db()
    with get_db() as db:
        user = db.query(User).filter(User.email == 'admin@nexabank.com').first()
        if not user:
            user = User(
                email='admin@nexabank.com',
                full_name='Admin User',
                password_hash=hash_password('Password123'),
                phone='+1234567890',
                is_admin=True
            )
            db.add(user)
            db.flush()
            db.refresh(user)
            print(f'Created user: {user.email}')
            
            # Set PIN
            set_pin(db, user.id, '1234')
            
            # Create Checking Account
            ok, msg, acct = open_account(
                db, user.id, AccountType.CHECKING,
                initial_deposit=5000.0,
                holder_name='Admin User',
                phone='+1234567890',
                currency='USD'
            )
            print(f'Created checking account: {acct}')
            
            # Create Savings Account
            ok, msg, acct2 = open_account(
                db, user.id, AccountType.SAVINGS,
                initial_deposit=12000.0,
                holder_name='Admin User',
                phone='+1234567890',
                currency='USD'
            )
            print(f'Created savings account: {acct2}')

if __name__ == '__main__':
    seed()
