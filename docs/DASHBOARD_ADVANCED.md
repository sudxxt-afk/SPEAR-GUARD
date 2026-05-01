# Dashboard Advanced Features - Complete Guide

## 🎯 Реализованные функции

### ✅ 1. Backend API Endpoints для реальных данных

**Файл:** [`backend/api/dashboard_analytics.py`](file:///c:/SPEAR-GUARD/backend/api/dashboard_analytics.py)

Созданы 5 новых endpoints:

#### GET /api/v1/dashboard/threat-trend
Возвращает динамику угроз за указанный период
```python
params: days (1-365, default: 7)
response: {
  "data": [{"date": "27.01", "threats": 45, "blocked": 30, "quarantined": 15}],
  "period": "7 days"
}
```

#### GET /api/v1/dashboard/attack-map
Возвращает географическое распределение атак
```python
params: hours (1-168, default: 24)
response: {
  "attacks": [{
    "id": 1,
    "lat": 55.7558,
    "lng": 37.6173,
    "city": "Moscow",
    "country": "Russia",
    "severity": "HIGH",
    "count": 12,
    "timestamp": "2026-01-27T..."
  }]
}
```

#### GET /api/v1/dashboard/activity-heatmap
Возвращает почасовую активность
```python
params: days (1-30, default: 7)
response: {
  "data": [{"hour": "00:00", "count": 5}, ...]
}
```

#### GET /api/v1/dashboard/risk-timeline
Возвращает timeline риска
```python
params: days (1-90, default: 14)
response: {
  "data": [{"timestamp": "27.01", "score": 65.5, "average": 45.2}]
}
```

#### GET /api/v1/dashboard/threat-details/{date}
Drill-down: детали угроз за конкретную дату
```python
params: date (YYYY-MM-DD)
response: {
  "date": "2026-01-27",
  "total_threats": 45,
  "threats": [{
    "id": 123,
    "from_address": "attacker@evil.com",
    "subject": "Phishing attempt",
    "risk_score": 85.5,
    ...
  }]
}
```

---

### ✅ 2. Фильтры по датам

**Файл:** [`frontend/src/components/DateFilter.tsx`](file:///c:/SPEAR-GUARD/frontend/src/components/DateFilter.tsx)

Красивый компонент выбора временного диапазона:

- **4 опции**: 7 дней, 14 дней, 30 дней, 90 дней
- **Активное состояние**: Синяя подсветка выбранного периода
- **Иконка календаря**: Lucide Calendar icon
- **Helper функция**: `parseDaysFromRange()` для конвертации

**Использование:**
```typescript
const [timeRange, setTimeRange] = useState<TimeRange>('7d');
<DateFilter value={timeRange} onChange={setTimeRange} />
```

---

### ✅ 3. Экспорт графиков в PNG/PDF

**Файлы:**
- [`frontend/src/utils/exportChart.ts`](file:///c:/SPEAR-GUARD/frontend/src/utils/exportChart.ts) - Утилиты экспорта
- [`frontend/src/components/ExportButton.tsx`](file:///c:/SPEAR-GUARD/frontend/src/components/ExportButton.tsx) - UI компонент

**Возможности:**
- ✅ **Экспорт в PNG**: Высокое разрешение (scale: 2)
- ✅ **Экспорт в PDF**: Автоматический размер страницы
- ✅ **Множественный экспорт**: Несколько графиков в один PDF
- ✅ **Темная тема**: Сохраняется в экспорте
- ✅ **Выпадающее меню**: PNG или PDF

**Библиотеки:**
- `html2canvas` - Конвертация DOM в canvas
- `jspdf` - Генерация PDF

**API:**
```typescript
// Одиночный экспорт
await exportToPNG('chart-id', { filename: 'threat-trend' });
await exportToPDF('chart-id', { filename: 'threat-trend' });

// Множественный экспорт
await exportMultipleToPDF(['chart1', 'chart2'], 'dashboard-report');
```

---

### ✅ 4. Анимации при загрузке данных

**Файл:** [`frontend/src/components/LoadingSkeleton.tsx`](file:///c:/SPEAR-GUARD/frontend/src/components/LoadingSkeleton.tsx)

**Компоненты:**

#### LoadingSkeleton
Красивый skeleton loader для графиков:
- ✅ Анимированные бары (pulse)
- ✅ Skeleton header и legend
- ✅ Настраиваемая высота
- ✅ Темная тема

#### FadeIn
Плавное появление контента:
- ✅ CSS анимация fadeIn
- ✅ Настраиваемая задержка
- ✅ Используется для последовательного появления

**Использование:**
```typescript
{loading ? (
  <LoadingSkeleton height={400} />
) : (
  <FadeIn delay={100}>
    <Chart data={data} />
  </FadeIn>
)}
```

---

### ✅ 5. Drill-down на графиках

**Файлы:**
- [`frontend/src/components/ThreatTrendChartEnhanced.tsx`](file:///c:/SPEAR-GUARD/frontend/src/components/ThreatTrendChartEnhanced.tsx) - График с drill-down
- [`frontend/src/components/DrillDownModal.tsx`](file:///c:/SPEAR-GUARD/frontend/src/components/DrillDownModal.tsx) - Модальное окно деталей

**Функциональность:**
- ✅ **Клик на дату**: Открывает модальное окно
- ✅ **Детали угроз**: Список всех угроз за дату
- ✅ **Информация**: From/To, Subject, Risk Score, Status, Decision
- ✅ **Цветовая индикация**: По severity
- ✅ **Красивый UI**: Иконки, бейджи, градиенты

**Как работает:**
1. Пользователь кликает на дату в tooltip графика
2. Вызывается `onDateClick(date)`
3. Загружаются детали через API `getThreatDetails(date)`
4. Открывается `DrillDownModal` с данными

---

## 📦 Новые зависимости

Добавлены в `package.json`:
```json
{
  "dependencies": {
    "axios": "^1.6.5",        // HTTP клиент
    "html2canvas": "^1.4.1",  // DOM → Canvas
    "jspdf": "^2.5.1"         // PDF генератор
  }
}
```

---

## 🚀 Установка и запуск

```bash
# Frontend
cd c:\SPEAR-GUARD\frontend
npm install  # Установить новые зависимости!
npm run dev

# Backend (в другом терминале)
cd c:\SPEAR-GUARD\backend
python main.py
```

---

## 🎨 Использование в Dashboard

### Пример интеграции:

```typescript
import { ThreatTrendChartEnhanced } from '../components/ThreatTrendChartEnhanced';
import { DrillDownModal } from '../components/DrillDownModal';
import { dashboardAnalyticsApi } from '../services/dashboardAnalytics';

export const Dashboard = () => {
  const [drillDownData, setDrillDownData] = useState(null);

  const handleDateClick = async (date: string) => {
    const data = await dashboardAnalyticsApi.getThreatDetails(date);
    setDrillDownData(data);
  };

  return (
    <>
      <ThreatTrendChartEnhanced onDateClick={handleDateClick} />
      
      {drillDownData && (
        <DrillDownModal
          date={drillDownData.date}
          threats={drillDownData.threats}
          totalThreats={drillDownData.total_threats}
          onClose={() => setDrillDownData(null)}
        />
      )}
    </>
  );
};
```

---

## 🔧 Созданные файлы

### Backend:
- ✅ `backend/api/dashboard_analytics.py` - API endpoints

### Frontend:
- ✅ `frontend/src/services/dashboardAnalytics.ts` - API service
- ✅ `frontend/src/components/DateFilter.tsx` - Фильтр дат
- ✅ `frontend/src/components/ExportButton.tsx` - Кнопка экспорта
- ✅ `frontend/src/components/LoadingSkeleton.tsx` - Анимации загрузки
- ✅ `frontend/src/components/ThreatTrendChartEnhanced.tsx` - Улучшенный график
- ✅ `frontend/src/components/DrillDownModal.tsx` - Модальное окно
- ✅ `frontend/src/utils/exportChart.ts` - Утилиты экспорта

---

## 📊 Скриншоты функций

### 1. Фильтр дат
Синяя подсветка активного периода, иконка календаря

### 2. Кнопка экспорта
Выпадающее меню с опциями PNG/PDF

### 3. Loading Skeleton
Анимированные бары с pulse эффектом

### 4. Drill-down Modal
Модальное окно с детальной информацией об угрозах

---

## 🎯 Следующие шаги

Для полной интеграции:

1. **Обновить Dashboard.tsx**:
   - Заменить mock компоненты на Enhanced версии
   - Добавить state для drill-down
   - Подключить все новые компоненты

2. **Создать Enhanced версии остальных графиков**:
   - AttackMapEnhanced
   - ActivityHeatmapEnhanced
   - RiskScoreTimelineEnhanced

3. **Добавить глобальный экспорт**:
   - Кнопка "Экспорт всего Dashboard"
   - Генерация PDF отчета со всеми графиками

4. **Оптимизация**:
   - Кэширование данных
   - Debounce для фильтров
   - Lazy loading для модалов

---

## 🐛 Известные ограничения

1. **GeoIP**: Сейчас используется mock mapping по доменам. Для production нужна GeoIP база (MaxMind)
2. **TypeScript**: Некоторые lint ошибки исчезнут после `npm install`
3. **Timezone**: Все даты в UTC, нужна локализация

---

## 💡 Советы по использованию

1. **Экспорт**: Лучше экспортировать после полной загрузки данных
2. **Drill-down**: Работает только на датах с данными
3. **Фильтры**: Изменение фильтра перезагружает данные
4. **Анимации**: Можно отключить для медленных устройств
