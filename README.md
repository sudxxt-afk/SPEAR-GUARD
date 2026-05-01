# 🛡️ SPEAR-GUARD

**Intelligent Anti-Phishing Platform for Government Sector**

SPEAR-GUARD is a comprehensive security solution designed to protect government employees from targeted phishing attacks (spear-phishing). The platform combines advanced email analysis, machine learning, and a trusted sender registry to provide real-time threat detection.

---

## 🎯 Features

- **Real-time Email Analysis** - Instant risk assessment using multiple detection engines
- **Trusted Registry** - Multi-level sender verification system
- **Browser Extension** - Visual security indicators directly in Gmail/Outlook
- **Security Dashboard** - Comprehensive threat monitoring and analytics
- **WebSocket Integration** - Real-time alerts and updates
- **Multi-factor Analysis** - Technical, linguistic, behavioral, and contextual evaluation

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Browser Extension (Chrome/Firefox)          │
│  Real-time email analysis with visual indicators        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (Python 3.11)              │
│  REST API + WebSocket + Analysis Engine                 │
└────────┬────────────────────┬────────────────┬──────────┘
         │                    │                │
    ┌────▼────┐         ┌─────▼─────┐    ┌────▼────┐
    │PostgreSQL│         │   Redis   │    │Elastic  │
    │    15    │         │     7     │    │search 8 │
    └──────────┘         └───────────┘    └─────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Git
- 4GB+ RAM available

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/spear-guard.git
   cd spear-guard
   ```

2. **Copy environment variables**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` file** (optional)
   ```bash
   # Change default passwords and secrets
   nano .env
   ```

4. **Start all services**
   ```bash
   docker-compose up -d
   ```

5. **Wait for services to be ready** (30-60 seconds)
   ```bash
   docker-compose logs -f
   ```

6. **Access the application**
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Frontend (dev): http://localhost:3000
   - Health Check: http://localhost:8000/health

---

## 📋 Service URLs

| Service       | URL                          | Credentials              |
|--------------|------------------------------|--------------------------|
| Backend API  | http://localhost:8000        | -                        |
| Swagger UI   | http://localhost:8000/docs   | -                        |
| ReDoc        | http://localhost:8000/redoc  | -                        |
| PostgreSQL   | localhost:5432               | postgres/postgres        |
| Redis        | localhost:6379               | -                        |
| Elasticsearch| http://localhost:9200        | -                        |

---

## 🧪 Testing

### Check Health Status

```bash
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00.000000",
  "services": {
    "redis": "healthy",
    "elasticsearch": "healthy",
    "database": "healthy"
  }
}
```

### Test API v1 Status

```bash
curl http://localhost:8000/api/v1/status
```

### Interactive API Testing

Visit http://localhost:8000/docs for Swagger UI with interactive API testing.

---

## 📁 Project Structure

```
spear-guard/
├── backend/                    # FastAPI backend application
│   ├── main.py                # Main application entry point
│   ├── database.py            # SQLAlchemy models and database setup
│   ├── redis_client.py        # Redis client wrapper
│   ├── elasticsearch_client.py # Elasticsearch client wrapper
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile             # Backend container configuration
│
├── frontend/                   # React frontend (to be implemented)
│   └── ...
│
├── extension/                  # Browser extension (to be implemented)
│   └── ...
│
├── docker/                     # Docker configurations
│   └── ...
│
├── docker-compose.yml          # Docker Compose orchestration
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

---

## 🔧 Development

### Backend Development

1. **Enter backend container**
   ```bash
   docker-compose exec backend bash
   ```

2. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

3. **Access Python shell**
   ```bash
   python
   >>> from database import *
   >>> from redis_client import redis_client
   >>> from elasticsearch_client import es_client
   ```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f redis
docker-compose logs -f elasticsearch
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Stop Services

```bash
# Stop all
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

---

## 🔐 Security Considerations

### Production Deployment

Before deploying to production:

1. **Change all default passwords** in `.env`
2. **Generate secure SECRET_KEY** and **JWT_SECRET_KEY**
3. **Enable HTTPS** with valid SSL certificates
4. **Configure firewall rules** (only expose necessary ports)
5. **Enable Elasticsearch security** (xpack.security.enabled=true)
6. **Set up backup strategy** for PostgreSQL
7. **Configure log rotation**
8. **Enable rate limiting** on API endpoints
9. **Review CORS settings** (remove localhost origins)

### Environment Variables

Critical variables to change:
- `SECRET_KEY` - Application secret key
- `JWT_SECRET_KEY` - JWT signing key
- `POSTGRES_PASSWORD` - Database password
- `SMTP_PASSWORD` - Email service password

---

## 📊 Database Models

### Users
- Government employees and security officers
- Role-based access control (user, security_officer, admin)

### EmailAnalysis
- Stores analysis results for all processed emails
- Risk scores and status tracking

### TrustedRegistry
- Multi-level trusted sender verification
- Organizational context

### PhishingReport
- User-reported phishing attempts
- Investigation workflow

### ThreatAlert
- System-wide threat notifications
- Severity levels and affected users

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 👥 Team

Developed for government sector cybersecurity by the SPEAR-GUARD team.

---

## 📞 Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/spear-guard/issues
- Email: support@spear-guard.gov.ru

---

## 🗺️ Roadmap

### Phase 1 (Current)
- ✅ Basic infrastructure setup
- ✅ Database models
- ✅ Redis caching
- ✅ Elasticsearch integration

### Phase 2 (Next)
- 🔄 Email analysis engine
- 🔄 Machine learning models
- 🔄 Browser extension
- 🔄 User authentication

### Phase 3 (Future)
- 📋 Advanced threat intelligence
- 📋 Sandbox analysis
- 📋 Automated response system
- 📋 Integration with SIEM systems

---

**Made with ❤️ for a safer government digital infrastructure**
