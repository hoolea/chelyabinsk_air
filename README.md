# Chelyabinsk Air Quality (Home Assistant Integration)
Интеграция для Home Assistant, позволяющая получать данные о качестве воздуха и погодных условиях в Челябинске с официального API мониторинга окружающей среды.

## 📡Источник данных
Данные берутся с государственного сервиса:

+ https://emc.gov74.ru

Используемый API:
```
https://emc.gov74.ru/uisem/portal/ad/services/getData.php?d=now&t=chelyabinsk-1
```
## 🚀 Возможности
#### 📊 Получение данных по качеству воздуха:
+ Аммиак (NH₃)
+ Диоксид азота (NO₂)
+ Оксид азота (NO)
+ Диоксид серы (SO₂)
+ Оксид углерода (CO)
+ Сероводород (H₂S)
+ PM10 (если доступно)
+ PM2.5 (если доступно)
#### 🌦 Метеоданные:
+ Температура
+ Влажность
+ Атмосферное давление
+ Скорость ветра
+ Направление ветра
#### 🏙 Поддержка нескольких станций мониторинга
#### 💾 Кэширование данных (в случае недоступности API)
#### 🔄 Автоматическое обновление данных каждые 10 минут
#### ⚙️ Настройка станций через UI (Options Flow)

## 🧩 Установка
#### 1. Через HACS (рекомендуется)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hoolea&repository=chelyabinsk_air&category=integration)
#### 2. Ручная установка
1. Скопируйте папку интеграции в: custom_components/chelyabinsk_air/
2. Перезапустите Home Assistant

## ⚙️ Настройка
1. Перейдите в: Настройки → Устройства и службы
2. Нажмите: Добавить интеграцию → Chelyabinsk Air
3. Выберите станции мониторинга

## 🏷 Сущности

#### Каждая станция создаёт набор сенсоров:

Пример:
```
sensor.chelyabinsk_<station>_temperatura
sensor.chelyabinsk_<station>_vlazhnost
sensor.chelyabinsk_<station>_dioksid_azota
...
```

Название в интерфейсе:
```
Челябинск (ГНС №73, пр. Победы, 198а) Температура
```

## 🔄 Обновление данных
+ API опрашивается каждые 10 минут
+ Используется фоновая задача
+ При ошибке API используются последние сохранённые данные

## 💾 Кэширование

+ Интеграция сохраняет данные в storage
+ автоматически загружает при старте
+ используется как fallback при недоступности API

## 🧪 Отладка

Для включения логов добавьте в configuration.yaml:
```
logger:
  logs:
    custom_components.chelyabinsk_air: debug
```

## 🤝 Вклад

Pull requests и идеи приветствуются!

## 📄 Лицензия

MIT
