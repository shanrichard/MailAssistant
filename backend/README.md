# MailAssistant Backend

AI-powered email assistant backend with Gmail integration.

## Quick Start

### 1. Environment Setup

Make sure you have the `.env` file in the project root with all required variables:

```bash
# Database
DATABASE_URL=postgresql://username@localhost:5432/mailassistant

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/callback

# Security
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-encryption-key

# LLM APIs
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

### 2. Database Setup

```bash
# Create and migrate database
alembic upgrade head
```

### 3. Start the Server

#### Development Mode (with auto-reload)
```bash
# From project root
source .venv/bin/activate
python start_backend.py
```

#### Production Mode
```bash
# From backend directory
source .venv/bin/activate
cd backend
python run_server.py
```

### 4. API Documentation

Once the server is running:
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Authentication: http://localhost:8000/api/auth/
- Gmail Integration: http://localhost:8000/api/gmail/

## Available Endpoints

### Authentication
- `GET /api/auth/google-auth-url` - Get Google OAuth URL
- `POST /api/auth/google` - Complete Google OAuth
- `GET /api/auth/status` - Check auth status
- `POST /api/auth/refresh` - Refresh tokens
- `DELETE /api/auth/logout` - Logout

### Gmail Integration
- `GET /api/gmail/profile` - Get Gmail profile
- `POST /api/gmail/sync` - Sync emails from Gmail
- `GET /api/gmail/recent` - Get recent emails
- `GET /api/gmail/unread` - Get unread emails
- `POST /api/gmail/search` - Search emails
- `POST /api/gmail/mark-read` - Mark emails as read

## Testing

Test the Gmail integration:
```bash
cd backend
python test_gmail_integration.py
```

## Development

The backend uses:
- **FastAPI** - Web framework
- **SQLAlchemy** - ORM
- **PostgreSQL** - Database
- **Google APIs** - Gmail integration
- **LangChain/LangGraph** - AI agents