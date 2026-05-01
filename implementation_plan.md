# Implementation Plan: User-Centric Architecture & Personal IMAP

## Goal
Transition the SPEAR-GUARD platform from a single-tenant shared environment to a multi-user system where:
1.  **Data Isolation:** Users only access their own data (or organization data if they are Security Officers).
2.  **Hierarchical Access:** Implementation of Roles (Admin -> Security Officer -> Employee).
3.  **Personal Integrations:** Users can connect their own multiple email accounts (IMAP) via the UI.
4.  **Dynamic Workers:** The system dynamically spawns tasks to monitor individual user mailboxes instead of a single global listener.

## User Review Required
> [!IMPORTANT]
> **Database Migration Required:** This plan involves significant changes to `users` table and creation of new tables (`mail_accounts`, `organizations`). Existing data might need manual migration strategies if preserving old "shared" data is required. Check if we can wipe current test data.
>
> **Secrets Management:** We will use `cryptography.fernet` to store IMAP passwords encrypted in the database. The encryption key must be managed securely in `.env`.

## Proposed Changes

### 1. Database Schema (`backend/database.py`)

#### [MODIFY] User Model
Add hierarchy fields and relation to Organization.
```python
class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    domain = Column(String) # Auto-assign users with this email domain
    # ... settings

class User(Base):
    # ... existing fields
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    role = Column(String) # 'admin', 'sec_officer', 'employee'
    mail_accounts = relationship("MailAccount", back_populates="owner")
```

#### [NEW] MailAccount Model
Store connection details for specific users.
```python
class MailAccount(Base):
    __tablename__ = "mail_accounts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Connection Details
    provider = Column(String) # 'gmail', 'outlook', 'custom'
    email = Column(String)
    imap_server = Column(String)
    imap_port = Column(Integer, default=993)
    username = Column(String)
    encrypted_password = Column(String) # Encrypted using Fernet
    
    # State
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime)
    status = Column(String) # 'connected', 'auth_error', 'syncing'
```

#### [MODIFY] EmailAnalysis Model
Link generic analysis results to specific users/accounts.
```python
class EmailAnalysis(Base):
    # ... existing fields
    # Ensure user_id is always populated
    mail_account_id = Column(Integer, ForeignKey("mail_accounts.id")) # Track which account received this
```

### 2. Backend Logic

#### [NEW] `backend/utils/crypto.py`
Helper for encrypting/decrypting user IMAP passwords.

#### [MODIFY] `backend/api/auth.py` & `backend/api/users.py`
- Update registration to handle organization logic (optional: auto-join org by domain).
- Update dependency `get_current_user` to return role context.

#### [NEW] `backend/api/mail_accounts.py`
CRUD endpoints for users to manage their IMAP connections:
- `POST /mail-accounts/connect` (Test connection & Save)
- `GET /mail-accounts/` (List my accounts)
- `DELETE /mail-accounts/{id}`
- `POST /mail-accounts/{id}/sync` (Force manual sync)

#### [REFACTOR] IMAP Integration (`backend/integrations/imap_listener.py`)
**Major Change:** Currently `imap_listener.py` is a standalone daemon process with global settings.
**New Approach:** 
1. Deprecate the standalone `imap-listener` container in `docker-compose.yml`.
2. Convert polling logic into a **Celery Task**.
3. Create a `scheduler` (Celery Beat) that runs `monitor_all_active_accounts` every X minutes.
4. `monitor_all_active_accounts` spawns individual jobs `sync_user_mailbox(account_id)` for every active account.

### 3. API Layer & Data Isolation

#### [MODIFY] `backend/api/analyze.py`, `backend/api/alerts.py`, etc.
Modify all `GET` endpoints (get_emails, get_alerts) to filter by user:

```python
# Pseudo-code pattern
if current_user.role == 'employee':
    query = query.filter(EmailAnalysis.user_id == current_user.id)
elif current_user.role == 'sec_officer':
    query = query.filter(User.organization_id == current_user.organization_id)
# Admin sees all (or filtered by org)
```

### 4. Frontend Changes (`frontend/src`)

#### [NEW] `pages/Settings/MailAccounts.tsx`
Interface for users to:
- See connected inboxes.
- "Add New Account" wizard (Select provider -> Enter Creds -> Test).
- View sync status (Green dot / Red dot).

#### [MODIFY] `contexts/AuthContext.tsx`
Store extended User object (with Role and Organization info).

#### [MODIFY] Dashboard & Layout
- If `role === 'employee'`, hide global statistics, show "My Threat Score".
- If `role === 'sec_officer'`, show Organization Dashboard.

## Verification Plan

### Automated Tests
1. **Crypto Test:** Verify password encryption/decryption roundtrip.
2. **Access Control Test:** Create User A and User B. Ensure User A cannot fetch User B's alerts via API.
3. **IMAP Connection Test:** Mock IMAP server, verify `sync_user_mailbox` task successfully connects using stored mocked credentials.

### Manual Verification
1. Log in as a fresh user.
2. Go to Settings -> Mail Accounts.
3. Add a real Gmail account (using App Password).
4. Verify backend logs show successful connection and sync start.
5. Check Dashboard: Should populate with emails ONLY from that account.
6. Log in as a second user. Dashboard should be empty until an account is added.
