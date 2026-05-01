# Dashboard Visualization Setup

## 📦 Установка зависимостей

После добавления визуальных компонентов необходимо установить новые библиотеки:

```bash
cd c:\SPEAR-GUARD\frontend
npm install
```

Это установит:
- **recharts** (^2.10.3) - библиотека для графиков
- **react-leaflet** (^4.2.1) - React обертка для Leaflet карт
- **leaflet** (^1.9.4) - библиотека интерактивных карт
- **@types/leaflet** (^1.9.8) - TypeScript типы для Leaflet

## 🎨 Созданные компоненты

### 1. ThreatTrendChart
**Файл:** `frontend/src/components/ThreatTrendChart.tsx`

Area chart для отображения динамики угроз за неделю/месяц/год.

**Особенности:**
- 3 линии: Угрозы, Заблокировано, Карантин
- Градиентная заливка
- Кастомный tooltip
- Легенда с цветовыми индикаторами

### 2. AttackMap
**Файл:** `frontend/src/components/AttackMap.tsx`

Интерактивная карта мира с точками атак.

**Особенности:**
- Темная тема карты (CartoDB Dark)
- Цветовая индикация severity (красный/оранжевый/желтый/синий)
- Размер маркера зависит от severity
- Popup с деталями атаки
- Автоматическое центрирование на атаках

### 3. ActivityHeatmap
**Файл:** `frontend/src/components/ActivityHeatmap.tsx`

Bar chart с распределением угроз по часам суток.

**Особенности:**
- Цветовая индикация интенсивности (0, 1-4, 5-9, 10-19, 20+)
- 24 столбца (по часам)
- Легенда с градацией

### 4. RiskScoreTimeline
**Файл:** `frontend/src/components/RiskScoreTimeline.tsx`

Line chart с изменением уровня риска во времени.

**Особенности:**
- 2 линии: текущий риск и средний
- Reference lines для уровней риска (25, 50, 75)
- Индикаторы уровней (Низкий/Средний/Высокий/Критический)
- Кастомный tooltip с уровнем риска

## 📊 Mock данные

**Файл:** `frontend/src/utils/mockData.ts`

Функции-генераторы для тестовых данных:
- `generateThreatTrendData()` - данные для графика угроз
- `generateAttackMapData()` - координаты атак по миру
- `generateActivityHeatmapData()` - активность по часам
- `generateRiskScoreTimelineData()` - timeline риска за 2 недели

## 🚀 Запуск

```bash
# Backend
cd c:\SPEAR-GUARD\backend
python main.py

# Frontend (новый терминал)
cd c:\SPEAR-GUARD\frontend
npm install  # ВАЖНО: установить новые зависимости!
npm run dev
```

Откройте `http://localhost:3000` и войдите в систему. На Dashboard вы увидите:

1. **Статистика** (4 карточки вверху)
2. **WebSocket статус** (🟢 Real-time подключен)
3. **Последние анализы и алерты** (2 колонки)
4. **📈 Threat Trend Chart** (график динамики угроз)
5. **🗺️ Attack Map + 🔥 Activity Heatmap** (2 колонки)
6. **📉 Risk Score Timeline** (график риска во времени)

## 🎨 Скриншоты компонентов

### Threat Trend Chart
- Area chart с 3 линиями
- Градиентная заливка
- Темная тема

### Attack Map
- Интерактивная карта мира
- Цветные маркеры атак
- Popup с деталями

### Activity Heatmap
- Bar chart по часам
- Цветовая градация

### Risk Score Timeline
- Line chart с reference lines
- Индикаторы уровней риска

## 🔧 Кастомизация

### Изменить временной диапазон
```typescript
<ThreatTrendChart data={data} timeRange="month" />
```

### Добавить реальные данные
Замените mock функции на API вызовы:
```typescript
const [threatData, setThreatData] = useState([]);

useEffect(() => {
  const loadData = async () => {
    const data = await dashboardApi.getThreatTrend();
    setThreatData(data);
  };
  loadData();
}, []);

<ThreatTrendChart data={threatData} />
```

## 📝 Следующие шаги

- [ ] Создать backend API endpoints для реальных данных
- [ ] Добавить фильтры по датам
- [ ] Экспорт графиков в PNG/PDF
- [ ] Анимации при загрузке данных
- [ ] Drill-down на графиках (клик для деталей)
