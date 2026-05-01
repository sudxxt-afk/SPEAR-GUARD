# ЧАСТЬ II: АРХИТЕКТУРА СИСТЕМЫ

## 5. ОБЩАЯ АРХИТЕКТУРА

### 5.1 Высокоуровневая архитектура

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            КЛИЕНТЫ                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │   Browser    │  │   Browser    │  │   Browser    │  │   Mobile    │ │
│  │  Extension   │  │  (Dashboard) │  │(User Portal) │  │     App     │ │
│  │              │  │              │  │              │  │  (Future)   │ │
│  │   Chrome     │  │   React 18   │  │   React 18   │  │             │ │
│  │   Firefox    │  │  TypeScript  │  │  TypeScript  │  │             │ │
│  │   Edge       │  │              │  │              │  │             │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘ │
└─────────┼──────────────────┼──────────────────┼──────────────────┼───────┘
          │                  │                  │                  │
          │    HTTPS/WSS     │                  │                  │
          └──────────────────┴──────────────────┴──────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     GATEWAY & БАЛАНСИРОВКА                               │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                        Nginx / Traefik                            │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │  │
│  │  │ SSL Term.  │  │    Load    │  │   Rate     │  │   WAF      │ │  │
│  │  │            │  │  Balancer  │  │  Limiter   │  │            │ │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     │                               │
                     ▼                               ▼
┌────────────────────────────────┐    ┌─────────────────────────────────┐
│       REST API SERVERS         │    │    WEBSOCKET SERVERS            │
│  ┌──────────────────────────┐ │    │  ┌───────────────────────────┐ │
│  │    FastAPI Instance 1    │ │    │  │  WebSocket Instance 1     │ │
│  │    (Uvicorn + Gunicorn)  │ │    │  │   (FastAPI WebSocket)     │ │
│  │  Port: 8000              │ │    │  │   Port: 8001              │ │
│  └──────────────────────────┘ │    │  └───────────────────────────┘ │
│  ┌──────────────────────────┐ │    │  ┌───────────────────────────┐ │
│  │    FastAPI Instance 2    │ │    │  │  WebSocket Instance 2     │ │
│  └──────────────────────────┘ │    │  └───────────────────────────┘ │
│  ┌──────────────────────────┐ │    │  ┌───────────────────────────┐ │
│  │    FastAPI Instance N    │ │    │  │  WebSocket Instance N     │ │
│  └──────────────────────────┘ │    │  └───────────────────────────┘ │
└────────────────┬───────────────┘    └───────────────┬─────────────────┘
                 │                                    │
                 └────────────────┬───────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       БИЗНЕС-ЛОГИКА (APPLICATION LAYER)                  │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    EMAIL ANALYSIS PIPELINE                       │   │
│  │                                                                   │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │  1. REGISTRY CHECKER                                       │ │   │
│  │  │     ├─ Lookup email in trusted registry                    │ │   │
│  │  │     ├─ Check trust level (1-4)                            │ │   │
│  │  │     ├─ Validate SPF/DKIM against known params             │ │   │
│  │  │     └─ Fast track if Level 1-2 + validated                │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │                               │                                  │   │
│  │                               ▼                                  │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │  2. MULTI-LAYER ANALYSIS ENGINE (Parallel Execution)      │ │   │
│  │  │                                                             │ │   │
│  │  │  ┌──────────────────────────────────────────────────────┐ │ │   │
│  │  │  │  TECHNICAL ANALYZER                                   │ │ │   │
│  │  │  │  ├─ SPF/DKIM/DMARC Validator                         │ │ │   │
│  │  │  │  ├─ Attachment Scanner (ClamAV + oletools)           │ │ │   │
│  │  │  │  ├─ URL Inspector (VirusTotal + homograph)           │ │ │   │
│  │  │  │  └─ Header Analysis                                  │ │ │   │
│  │  │  │  Output: technical_score ∈ [0, 100]                  │ │ │   │
│  │  │  └──────────────────────────────────────────────────────┘ │ │   │
│  │  │                                                             │ │   │
│  │  │  ┌──────────────────────────────────────────────────────┐ │ │   │
│  │  │  │  LINGUISTIC ANALYZER (NLP)                           │ │ │   │
│  │  │  │  ├─ Social Engineering Detector                      │ │ │   │
│  │  │  │  ├─ ruBERT Embeddings (DeepPavlov)                   │ │ │   │
│  │  │  │  ├─ Style Analysis (spaCy)                           │ │ │   │
│  │  │  │  ├─ XGBoost Phishing Classifier                      │ │ │   │
│  │  │  │  └─ Sentiment Analysis                               │ │ │   │
│  │  │  │  Output: linguistic_score ∈ [0, 100]                 │ │ │   │
│  │  │  └──────────────────────────────────────────────────────┘ │ │   │
│  │  │                                                             │ │   │
│  │  │  ┌──────────────────────────────────────────────────────┐ │ │   │
│  │  │  │  BEHAVIORAL ANALYZER                                 │ │ │   │
│  │  │  │  ├─ Sender Profile Builder                          │ │ │   │
│  │  │  │  ├─ Anomaly Detector (Isolation Forest)             │ │ │   │
│  │  │  │  ├─ Temporal Pattern Matcher                        │ │ │   │
│  │  │  │  ├─ Geographic Anomaly Detector                     │ │ │   │
│  │  │  │  └─ Frequency Analyzer                              │ │ │   │
│  │  │  │  Output: behavioral_score ∈ [0, 100]                │ │ │   │
│  │  │  └──────────────────────────────────────────────────────┘ │ │   │
│  │  │                                                             │ │   │
│  │  │  ┌──────────────────────────────────────────────────────┐ │ │   │
│  │  │  │  CONTEXTUAL ANALYZER                                 │ │ │   │
│  │  │  │  ├─ Job Role Checker (AD integration)               │ │ │   │
│  │  │  │  ├─ Pretexting Detector                             │ │ │   │
│  │  │  │  ├─ Clearance Level Validator                       │ │ │   │
│  │  │  │  ├─ Topic Relevance Checker                         │ │ │   │
│  │  │  │  └─ Project Context Validator                       │ │ │   │
│  │  │  │  Output: contextual_score ∈ [0, 100]                │ │ │   │
│  │  │  └──────────────────────────────────────────────────────┘ │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │                               │                                  │   │
│  │                               ▼                                  │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │  3. DECISION ENGINE                                        │ │   │
│  │  │     ├─ Aggregate risk scores (weighted sum)               │ │   │
│  │  │     ├─ Apply business rules                               │ │   │
│  │  │     ├─ Generate explanation                               │ │   │
│  │  │     └─ Make decision (DELIVER/QUARANTINE/BLOCK)          │ │   │
│  │  │     Output: Action + Risk_Score + Explanation             │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │                               │                                  │   │
│  │                               ▼                                  │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │  4. ACTION EXECUTOR                                        │ │   │
│  │  │     ├─ Execute decision (deliver/quarantine/block)        │ │   │
│  │  │     ├─ Send notifications (WebSocket, Email, SMS)         │ │   │
│  │  │     ├─ Update database                                    │ │   │
│  │  │     ├─ Log to Elasticsearch                               │ │   │
│  │  │     └─ Update metrics (Prometheus)                        │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    SUPPORTING SERVICES                           │   │
│  │                                                                   │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │   │
│  │  │  Registry Auto-  │  │  Profile         │  │  ML Model     │ │   │
│  │  │  Populator       │  │  Builder         │  │  Training     │ │   │
│  │  │                  │  │                  │  │  Service      │ │   │
│  │  │  - Analyze hist. │  │  - Build sender  │  │  - Retrain    │ │   │
│  │  │  - Calculate TL  │  │    profiles      │  │  - Evaluate   │ │   │
│  │  │  - Auto-add      │  │  - Update stats  │  │  - Deploy     │ │   │
│  │  │  Schedule: daily │  │  Schedule: hourly│  │  Schedule: 7d │ │   │
│  │  └──────────────────┘  └──────────────────┘  └───────────────┘ │   │
│  │                                                                   │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │   │
│  │  │  Alert           │  │  Report          │  │  Notification │ │   │
│  │  │  Manager         │  │  Generator       │  │  Service      │ │   │
│  │  │                  │  │                  │  │               │ │   │
│  │  │  - Triage alerts │  │  - PDF reports   │  │  - Email      │ │   │
│  │  │  - Correlate     │  │  - Dashboards    │  │  - SMS        │ │   │
│  │  │  - Escalate      │  │  - Analytics     │  │  - Telegram   │ │   │
│  │  └──────────────────┘  └──────────────────┘  └───────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      BACKGROUND WORKERS (Celery)                         │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ Worker Pool  │  │ Worker Pool  │  │ Worker Pool  │  │ Beat       │ │
│  │ #1 (Analysis)│  │ #2 (Registry)│  │ #3 (Reports) │  │ Scheduler  │ │
│  │              │  │              │  │              │  │            │ │
│  │ Tasks:       │  │ Tasks:       │  │ Tasks:       │  │ Periodic   │ │
│  │ - Email scan │  │ - Auto-pop   │  │ - Gen reports│  │ tasks mgmt │ │
│  │ - Attachment │  │ - Profile    │  │ - Cleanup    │  │            │ │
│  │   analysis   │  │   building   │  │ - Archive    │  │            │ │
│  │ - URL check  │  │ - Stats      │  │ - ML train   │  │            │ │
│  │              │  │   update     │  │              │  │            │ │
│  │ Concurrency: │  │ Concurrency: │  │ Concurrency: │  │            │ │
│  │ 8 workers    │  │ 4 workers    │  │ 2 workers    │  │            │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘ │
│         └──────────────────┴────────────────┴──────────────────┘        │
│                                    │                                     │
│                         ┌──────────▼──────────┐                         │
│                         │   RabbitMQ Broker   │                         │
│                         │   ┌──────────────┐  │                         │
│                         │   │ Queue: email │  │                         │
│                         │   │ Queue: reg   │  │                         │
│                         │   │ Queue: report│  │                         │
│                         │   └──────────────┘  │                         │
│                         └─────────────────────┘                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                      │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    PostgreSQL 15 (Primary DB)                     │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │  │
│  │  │   Master   │  │  Replica 1 │  │  Replica 2 │  │  Replica N │ │  │
│  │  │  (Write)   │  │   (Read)   │  │   (Read)   │  │   (Read)   │ │  │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘ │  │
│  │        │                │                │                │        │  │
│  │        └────────────────┴────────────────┴────────────────┘        │  │
│  │                      Streaming Replication                         │  │
│  │                                                                     │  │
│  │  Tables:                                                            │  │
│  │  ├─ trusted_registry (доверенные адреса)                          │  │
│  │  ├─ relationships (связи между пользователями)                    │  │
│  │  ├─ anomalies (аномалии в поведении)                             │  │
│  │  ├─ email_analysis (результаты анализа)                          │  │
│  │  ├─ phishing_reports (отчеты от пользователей)                   │  │
│  │  ├─ sender_profiles (профили отправителей)                       │  │
│  │  ├─ recipient_profiles (профили получателей)                     │  │
│  │  ├─ users (пользователи системы)                                 │  │
│  │  ├─ alerts (алерты безопасности)                                 │  │
│  │  └─ audit_log (аудит действий)                                   │  │
│  │                                                                     │  │
│  │  Connection Pool: PgBouncer (transaction mode)                     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                       Redis 7 (Cache + Queue)                     │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                  │  │
│  │  │   Master   │  │  Replica 1 │  │  Replica 2 │                  │  │
│  │  │            │  │            │  │            │                  │  │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                  │  │
│  │        │                │                │                         │  │
│  │        └────────────────┴────────────────┘                         │  │
│  │              Redis Sentinel (HA + Failover)                        │  │
│  │                                                                     │  │
│  │  Use cases:                                                         │  │
│  │  ├─ Registry cache (TTL: 15min)                                   │  │
│  │  ├─ Session storage (JWT tokens)                                  │  │
│  │  ├─ Rate limiting (sliding window)                                │  │
│  │  ├─ Pub/Sub (WebSocket events)                                    │  │
│  │  ├─ Task queue (Celery broker fallback)                           │  │
│  │  └─ Temporary results                                             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   Elasticsearch 8 (Search + Logs)                 │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                  │  │
│  │  │   Node 1   │  │   Node 2   │  │   Node 3   │                  │  │
│  │  │  (Master)  │  │   (Data)   │  │   (Data)   │                  │  │
│  │  └────────────┘  └────────────┘  └────────────┘                  │  │
│  │                                                                     │  │
│  │  Indices:                                                           │  │
│  │  ├─ spearguard-emails-* (архив писем, rotation: monthly)         │  │
│  │  ├─ spearguard-threats-* (каталог угроз)                         │  │
│  │  ├─ spearguard-logs-* (логи приложения)                          │  │
│  │  └─ spearguard-alerts-* (история алертов)                        │  │
│  │                                                                     │  │
│  │  Features:                                                          │  │
│  │  ├─ Full-text search (морфология русского языка)                 │  │
│  │  ├─ Aggregations (статистика)                                    │  │
│  │  ├─ Time-series data                                              │  │
│  │  └─ Machine Learning (anomaly detection)                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   MinIO (Object Storage S3-compatible)            │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                  │  │
│  │  │   Node 1   │  │   Node 2   │  │   Node 3   │  │   Node 4   │ │  │
│  │  │            │  │            │  │            │  │            │ │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘ │  │
│  │           Distributed mode (Erasure Coding 4+4)                    │  │
│  │                                                                     │  │
│  │  Buckets:                                                           │  │
│  │  ├─ quarantine/ (карантинированные вложения)                     │  │
│  │  ├─ sandbox-results/ (отчеты Cuckoo Sandbox)                     │  │
│  │  ├─ ml-models/ (артефакты ML-моделей)                            │  │
│  │  ├─ reports/ (сгенерированные PDF-отчеты)                        │  │
│  │  └─ backups/ (бэкапы БД)                                         │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL INTEGRATIONS                                 │
│                                                                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐ │
│  │ Active Directory │  │  Email Gateway   │  │  External APIs       │ │
│  │ (LDAP/LDAPS)     │  │  (Exchange/SMTP) │  │                      │ │
│  │                  │  │                  │  │  ┌────────────────┐  │ │
│  │ - User profiles  │  │ - Receive emails │  │  │ VirusTotal     │  │ │
│  │ - Org structure  │  │ - Send emails    │  │  │ (URL/file rep) │  │ │
│  │ - Departments    │  │ - Quarantine     │  │  └────────────────┘  │ │
│  │ - Positions      │  │ - Filters        │  │  ┌────────────────┐  │ │
│  │ - Permissions    │  │                  │  │  │ WHOIS API      │  │ │
│  │                  │  │                  │  │  │ (domain age)   │  │ │
│  └──────────────────┘  └──────────────────┘  │  └────────────────┘  │ │
│                                                │  ┌────────────────┐  │ │
│  ┌──────────────────┐  ┌──────────────────┐  │  │ GeoIP Service  │  │ │
│  │ SIEM Integration │  │  Cuckoo Sandbox  │  │  │ (geolocation)  │  │ │
│  │ (Optional)       │  │  (Malware anal.) │  │  └────────────────┘  │ │
│  │                  │  │                  │  │  ┌────────────────┐  │ │
│  │ - Send events    │  │ - Submit files   │  │  │ Threat Intel   │  │ │
│  │ - Correlate      │  │ - Get reports    │  │  │ Feeds (OSINT)  │  │ │
│  │                  │  │                  │  │  └────────────────┘  │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    MONITORING & OBSERVABILITY                            │
│                                                                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐ │
│  │  Prometheus      │  │     Grafana      │  │   ELK Stack          │ │
│  │  (Metrics)       │  │  (Dashboards)    │  │                      │ │
│  │                  │  │                  │  │  Elasticsearch       │ │
│  │ - App metrics    │  │ - Real-time viz  │  │  Logstash            │ │
│  │ - System metrics │  │ - Alerts         │  │  Kibana              │ │
│  │ - Custom metrics │  │ - Annotations    │  │                      │ │
│  └──────────────────┘  └──────────────────┘  │ - Log aggregation    │ │
│                                                │ - Search & analysis  │ │
│  ┌──────────────────┐  ┌──────────────────┐  └──────────────────────┘ │
│  │  Sentry          │  │   Jaeger         │                            │
│  │  (Error track)   │  │  (Distributed    │                            │
│  │                  │  │   tracing)       │                            │
│  │ - Exception logs │  │                  │                            │
│  │ - Stack traces   │  │ - Request traces │                            │
│  │ - Performance    │  │ - Latency anal.  │                            │
│  └──────────────────┘  └──────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Детали компонентов по слоям

#### 5.2.1 Presentation Layer (Клиентский слой)

**Браузерное расширение:**
```javascript
// Архитектура расширения
Extension/
├── manifest.json (v3)
│   - permissions: storage, webRequest, tabs
│   - host_permissions: mail.google.com, outlook.office.com
│   - content_scripts: inject в email clients
│   - background: service worker
│
├── background/
│   ├── service-worker.js
│   │   ├── WebSocket connection to backend
│   │   ├── API calls (fetch)
│   │   ├── Local cache management (IndexedDB)
│   │   ├── Notification handler
│   │   └── Message passing (chrome.runtime.sendMessage)
│   │
│   └── websocket-client.js
│       ├── Auto-reconnect logic
│       ├── Heartbeat/ping
│       └── Event handlers
│
├── content/
│   ├── gmail-content.js
│   │   ├── DOM observer (MutationObserver)
│   │   ├── Email list detection
│   │   ├── Indicator injection
│   │   └── Event listeners (clicks)
│   │
│   ├── outlook-content.js
│   └── yandex-content.js
│
├── popup/
│   ├── popup.html
│   ├── popup.js
│   │   ├── Stats display
│   │   ├── Quick check form
│   │   └── Settings link
│   └── popup.css
│
└── components/
    ├── risk-indicator.js (🟢🟡🟠🔴)
    ├── detail-panel.js
    └── notification-toast.js
```

**React Frontend (Dashboard):**
```typescript
// Архитектура SPA
frontend/src/
├── App.tsx (Root component)
│   - Router setup
│   - Auth context provider
│   - WebSocket context provider
│   - Theme provider
│
├── pages/
│   ├── Dashboard/
│   │   ├── Dashboard.tsx
│   │   │   └─ useEffect: fetch stats, setup WebSocket
│   │   ├── StatCard.tsx
│   │   ├── AlertsTable.tsx
│   │   ├── AttackMap.tsx (react-leaflet)
│   │   └── ThreatTrendChart.tsx (recharts)
│   │
│   ├── Registry/
│   │   ├── RegistryList.tsx
│   │   │   └─ react-table with sorting/filtering
│   │   ├── RegistryDetail.tsx
│   │   ├── RegistryForm.tsx (react-hook-form + yup)
│   │   └── PendingApprovals.tsx
│   │
│   ├── Alerts/
│   │   ├── AlertsList.tsx
│   │   ├── AlertDetail.tsx
│   │   └── AlertFilters.tsx
│   │
│   └── Reports/
│       ├── ReportBuilder.tsx
│       └── ReportPreview.tsx
│
├── components/
│   ├── Layout/
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx (react-router NavLink)
│   │   └── Footer.tsx
│   │
│   ├── shared/
│   │   ├── RiskIndicator.tsx
│   │   ├── DataTable.tsx
│   │   ├── Modal.tsx
│   │   └── Loading.tsx
│
├── services/
│   ├── api.ts (axios instance with interceptors)
│   ├── dashboardApi.ts
│   ├── registryApi.ts
│   └── websocket.ts
│       - socket.io-client
│       - event handlers
│       - reconnection logic
│
├── hooks/
│   ├── useAuth.ts
│   │   - login/logout
│   │   - token management
│   │   - refresh token
│   │
│   ├── useWebSocket.ts
│   │   - connection management
│   │   - subscribe to events
│   │   - emit events
│   │
│   └── useRegistry.ts
│       - CRUD operations
│       - optimistic updates
│
├── contexts/
│   ├── AuthContext.tsx
│   │   - user state
│   │   - permissions
│   │
│   └── WebSocketContext.tsx
│       - socket instance
│       - connection state
│       - message queue
│
└── types/
    ├── email.d.ts
    ├── registry.d.ts
    └── api.d.ts
```

#### 5.2.2 API Gateway Layer

**Nginx конфигурация:**
```nginx
# /etc/nginx/nginx.conf

upstream api_backend {
    least_conn;
    server api1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server api2:8000 weight=1 max_fails=3 fail_timeout=30s;
    server api3:8000 weight=1 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

upstream websocket_backend {
    ip_hash;  # Sticky sessions for WebSocket
    server ws1:8001;
    server ws2:8001;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=ws_limit:10m rate=5r/s;

# Connection limiting
limit_conn_zone $binary_remote_addr zone=addr:10m;

server {
    listen 443 ssl http2;
    server_name spear-guard.gov.ru;
    
    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'" always;
    
    # Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;
    
    # Frontend static files
    location / {
        root /var/www/frontend;
        try_files $uri $uri/ /index.html;
        expires 1h;
    }
    
    # API endpoints
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        limit_conn addr 10;
        
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # CORS
        add_header Access-Control-Allow-Origin $http_origin always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
        
        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }
    
    # WebSocket endpoint
    location /ws {
        limit_req zone=ws_limit burst=5 nodelay;
        
        proxy_pass http://websocket_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        proxy_pass http://api_backend;
    }
    
    # Metrics (restricted to monitoring network)
    location /metrics {
        allow 10.0.0.0/8;  # Internal network only
        deny all;
        
        proxy_pass http://api_backend;
    }
}

# HTTP → HTTPS redirect
server {
    listen 80;
    server_name spear-guard.gov.ru;
    return 301 https://$server_name$request_uri;
}
```

#### 5.2.3 Application Layer (Backend)

**FastAPI структура:**
```python
# main.py - полная версия с middleware stack

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
import time
import logging

app = FastAPI(
    title="SPEAR-GUARD API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Middleware stack (порядок важен!)

# 1. Trusted hosts (security)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["spear-guard.gov.ru", "*.spear-guard.gov.ru"]
)

# 2. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://spear-guard.gov.ru"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"]
)

# 3. Session management
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key",
    session_cookie="spear_guard_session",
    max_age=3600,
    same_site="lax",
    https_only=True
)

# 4. Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 5. Custom middleware - Request ID
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# 6. Custom middleware - Logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    logger.info(f"Request: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} ({process_time:.3f}s)")
    
    response.headers["X-Process-Time"] = str(process_time)
    return response

# 7. Custom middleware - Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 8. Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"}
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error(f"Internal error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Dependency injection
async def get_db():
    """Database session dependency"""
    async with AsyncSession() as session:
        yield session

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_email(db, email)
    if user is None:
        raise credentials_exception
    
    return user

# Include routers
from api import auth, registry, analyze, alerts, reports, extension

app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

app.include_router(
    registry.router,
    prefix="/api/v1/registry",
    tags=["Registry"],
    dependencies=[Depends(get_current_user)]  # Protected routes
)

app.include_router(
    analyze.router,
    prefix="/api/v1/analyze",
    tags=["Analysis"],
    dependencies=[Depends(get_current_user)]
)

# ... other routers

# Startup/Shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    logger.info("Starting SPEAR-GUARD backend...")
    
    # Database connection pool
    await init_db_pool()
    
    # Redis connection
    await redis_client.ping()
    logger.info("✓ Redis connected")
    
    # Elasticsearch
    if await es_client.ping():
        logger.info("✓ Elasticsearch connected")
    
    # Load ML models
    await load_ml_models()
    logger.info("✓ ML models loaded")
    
    # Start background tasks
    asyncio.create_task(registry_auto_populator())
    asyncio.create_task(profile_builder())
    
    logger.info("✓ SPEAR-GUARD backend ready")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down SPEAR-GUARD backend...")
    
    await close_db_pool()
    await redis_client.close()
    await es_client.close()
    
    logger.info("✓ Shutdown complete")
```
