# WebSocket Real-Time Notifications

## Обзор

SPEAR-GUARD использует WebSocket для доставки уведомлений в реальном времени:
- 🚨 Алерты безопасности
- 📧 Результаты анализа писем
- 📋 Обновления реестра доверенных отправителей
- ⚠️ Системные уведомления

## Архитектура

```
┌─────────────┐         WebSocket          ┌──────────────┐
│   Client    │◄──────────────────────────►│   Backend    │
│ (Dashboard/ │     ws://host/ws/{id}      │  Connection  │
│ Extension)  │                             │   Manager    │
└─────────────┘                             └──────────────┘
                                                    │
                                            ┌───────┴───────┐
                                            │               │
                                      ┌─────▼─────┐   ┌────▼────┐
                                      │  Alerts   │   │Registry │
                                      │  Service  │   │ Service │
                                      └───────────┘   └─────────┘
```

## Подключение

### JavaScript (Browser/Extension)

```javascript
// 1. Получить JWT токен через /api/v1/auth/login
const token = "your_jwt_token_here";
const userId = 123;

// 2. Подключиться к WebSocket
const ws = new WebSocket(
  `ws://localhost:8000/ws/${userId}?token=${token}&client_type=dashboard`
);

// 3. Обработка событий
ws.onopen = () => {
  console.log("✓ WebSocket connected");
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Received:", data);
  
  switch(data.type) {
    case "connection_established":
      console.log("Connection confirmed:", data.message);
      break;
      
    case "alert":
      handleAlert(data.data);
      break;
      
    case "email_analysis":
      handleEmailAnalysis(data.data);
      break;
      
    case "registry_update":
      handleRegistryUpdate(data.data);
      break;
      
    case "ping":
      // Respond to heartbeat
      ws.send(JSON.stringify({ type: "pong" }));
      break;
  }
};

ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};

ws.onclose = () => {
  console.log("WebSocket disconnected");
  // Implement reconnection logic
};

// 4. Отправка сообщений
function sendPong() {
  ws.send(JSON.stringify({ type: "pong" }));
}
```

### Python (Testing/Integration)

```python
import asyncio
import websockets
import json

async def connect_websocket():
    token = "your_jwt_token_here"
    user_id = 123
    
    uri = f"ws://localhost:8000/ws/{user_id}?token={token}&client_type=test"
    
    async with websockets.connect(uri) as websocket:
        print("✓ Connected to WebSocket")
        
        # Listen for messages
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data['type']}")
            
            if data['type'] == 'ping':
                # Respond to heartbeat
                await websocket.send(json.dumps({"type": "pong"}))

# Run
asyncio.run(connect_websocket())
```

## Типы сообщений

### 1. Connection Established
Отправляется при успешном подключении.

```json
{
  "type": "connection_established",
  "message": "Connected to SPEAR-GUARD real-time notifications",
  "user_id": 123,
  "timestamp": "2026-01-27T19:00:00.000Z"
}
```

### 2. Alert
Уведомление о новом алерте безопасности.

```json
{
  "type": "alert",
  "data": {
    "id": 456,
    "type": "PHISHING_DETECTED",
    "severity": "HIGH",
    "title": "Suspicious email detected",
    "message": "Email from unknown sender with malicious links",
    "sender_email": "attacker@evil.com",
    "recipient_email": "user@ministry.gov.ru",
    "created_at": "2026-01-27T19:00:00.000Z"
  },
  "timestamp": "2026-01-27T19:00:00.000Z"
}
```

### 3. Email Analysis
Результат анализа письма.

```json
{
  "type": "email_analysis",
  "data": {
    "message_id": "<abc123@example.com>",
    "from_address": "sender@example.com",
    "to_address": "recipient@ministry.gov.ru",
    "subject": "Important Document",
    "risk_score": 75.5,
    "status": "warning",
    "in_registry": false,
    "analyzed_at": "2026-01-27T19:00:00.000Z"
  },
  "timestamp": "2026-01-27T19:00:00.000Z"
}
```

### 4. Registry Update
Обновление реестра доверенных отправителей.

```json
{
  "type": "registry_update",
  "data": {
    "action": "added",
    "email_address": "director@ministry.gov.ru",
    "trust_level": 1,
    "status": "active",
    "timestamp": "2026-01-27T19:00:00.000Z"
  },
  "timestamp": "2026-01-27T19:00:00.000Z"
}
```

### 5. Ping/Pong (Heartbeat)
Проверка активности соединения (каждые 30 секунд).

**Server → Client:**
```json
{
  "type": "ping",
  "timestamp": "2026-01-27T19:00:00.000Z"
}
```

**Client → Server:**
```json
{
  "type": "pong"
}
```

### 6. Threat Alert
Критическое уведомление об обнаруженной угрозе.

```json
{
  "type": "threat_alert",
  "data": {
    "threat_type": "mass_phishing",
    "severity": "critical",
    "description": "Coordinated phishing campaign detected",
    "source": "multiple",
    "indicators": ["domain: evil.com", "ip: 1.2.3.4"],
    "detected_at": "2026-01-27T19:00:00.000Z"
  },
  "timestamp": "2026-01-27T19:00:00.000Z"
}
```

## API Endpoints

### WebSocket Connection
```
WS /ws/{user_id}?token={jwt_token}&client_type={type}
```

**Parameters:**
- `user_id` (path) - User ID
- `token` (query) - JWT authentication token
- `client_type` (query) - Client type: `dashboard`, `extension`, `mobile`

### Statistics
```
GET /ws/stats
Authorization: Bearer {token}
```

**Response:**
```json
{
  "active_connections": 15,
  "active_users": 12,
  "total_connections_ever": 1234,
  "total_messages_sent": 56789,
  "connections_by_type": {
    "dashboard": 8,
    "extension": 7
  }
}
```

## Интеграция в код

### Отправка алерта
```python
from websocket_integration import notify_alert_created

# При создании нового алерта
alert_data = {
    "id": alert.id,
    "alert_type": "PHISHING_DETECTED",
    "severity": "HIGH",
    "title": "Suspicious email",
    # ... другие поля
}

await notify_alert_created(alert_data)
```

### Отправка результата анализа
```python
from websocket_integration import notify_email_analysis_complete

analysis_data = {
    "message_id": "<abc@example.com>",
    "risk_score": 85.0,
    "status": "danger",
    # ... другие поля
}

await notify_email_analysis_complete(analysis_data, user_id=123)
```

### Обновление реестра
```python
from websocket_integration import notify_registry_updated

await notify_registry_updated(
    action="added",
    email_address="new@ministry.gov.ru",
    trust_level=2,
    status="active"
)
```

## Reconnection Strategy

Рекомендуемая стратегия переподключения:

```javascript
class WebSocketClient {
  constructor(userId, token) {
    this.userId = userId;
    this.token = token;
    this.reconnectDelay = 1000; // Start with 1 second
    this.maxReconnectDelay = 30000; // Max 30 seconds
    this.connect();
  }
  
  connect() {
    this.ws = new WebSocket(
      `ws://localhost:8000/ws/${this.userId}?token=${this.token}&client_type=dashboard`
    );
    
    this.ws.onopen = () => {
      console.log("✓ Connected");
      this.reconnectDelay = 1000; // Reset delay
    };
    
    this.ws.onclose = () => {
      console.log("Disconnected, reconnecting...");
      setTimeout(() => this.connect(), this.reconnectDelay);
      
      // Exponential backoff
      this.reconnectDelay = Math.min(
        this.reconnectDelay * 2,
        this.maxReconnectDelay
      );
    };
    
    this.ws.onmessage = (event) => {
      this.handleMessage(JSON.parse(event.data));
    };
  }
  
  handleMessage(data) {
    // Handle different message types
  }
}
```

## Безопасность

1. **Аутентификация:** Все соединения требуют валидный JWT токен
2. **Авторизация:** User ID в пути должен совпадать с user ID в токене
3. **Heartbeat:** Автоматическая проверка активности каждые 30 секунд
4. **Таймауты:** Неактивные соединения автоматически закрываются

## Мониторинг

Проверка статистики WebSocket:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/ws/stats
```

## Troubleshooting

### Ошибка подключения
- Проверьте валидность JWT токена
- Убедитесь, что user_id совпадает с токеном
- Проверьте CORS настройки

### Частые отключения
- Проверьте сетевое соединение
- Убедитесь, что клиент отвечает на ping
- Проверьте логи backend

### Не приходят уведомления
- Проверьте, что соединение активно
- Убедитесь, что обработчик `onmessage` настроен
- Проверьте фильтры событий
