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
+ Озон (O₃) и формальдегид (если станция их измеряет)
+ PM10 и PM2.5 (если доступно)
+ Наибольший СИ по станции

> Значения загрязнителей — это **стандартный индекс (СИ)**, как на портале emc.gov74.ru:
> концентрация, делённая на максимально разовую ПДК. Величина безразмерная:
> `1` — ровно ПДК, больше `1` — превышение. Это не µg/m³.

#### 🌦 Метеоданные:
+ Температура
+ Влажность
+ Атмосферное давление
+ Скорость ветра
+ Направление ветра
#### 🏙 Поддержка нескольких станций мониторинга
#### 💾 Кэширование данных (в случае недоступности API)
#### 🔄 Автоматическое обновление данных каждые 10 минут с повторными попытками
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
+ API отвечает медленно — обычно около 5 минут. Интеграция это учитывает:
  + таймаут запроса — 10 минут;
  + новый запрос стартует примерно через 10 минут после **начала** предыдущего, поэтому новые значения появляются раз в ~10 минут, а не раз в 15;
  + одновременно идёт только один запрос: ручное обновление во время текущего запроса не запускает второй.
+ Если запрос оборвался быстро (ошибка соединения, HTML-заглушка), он повторяется один раз через 30 секунд
+ Пока API недоступен, сенсоры показывают последние полученные значения
+ Если данные станции не обновлялись больше 3 часов, её сенсоры становятся «Недоступно»
+ Метеоданные на сервере обновляются раз в 6 часов; время измерения — в атрибуте `measured_at`, время последнего получения данных — в `data_updated`
+ Давление станций, которые отдают его в гПа (ГНС №72, №73 и др.), автоматически пересчитывается в мм рт. ст.
+ Ручное обновление: действие `homeassistant.update_entity` для любого сенсора

### ⏱ Время ответа API
Диагностический сенсор `sensor.chelyabinsk_air_vremia_otveta_api` показывает, сколько секунд шёл последний ответ.
Атрибут `average_seconds` — среднее по последним 30 запросам; на графике сенсора видна вся история.

## 💾 Кэширование данных (в случае недоступности API)
#### 🔄 Автоматическое обновление данных каждые 10 минут с повторными попытками
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
+ API опрашивается каждые 10 минут (стандартный `DataUpdateCoordinator` Home Assistant)
+ При сбое запрос повторяется до 3 раз с паузой 20 секунд
+ Если API недоступен, сенсоры показывают последние полученные значения
+ Если данные станции не обновлялись больше 3 часов, её сенсоры становятся «Недоступно» — чтобы устаревшие значения не выдавались за актуальные
+ Время последнего обновления станции — в атрибуте `data_updated` каждого сенсора
+ Можно обновить вручную: действие `homeassistant.update_entity` для любого сенсора

## 💾 Кэширование

+ Интеграция сохраняет данные в storage
+ при старте Home Assistant сразу показывает данные из кэша, а свежие загружает в фоне (медленный API не тормозит запуск)
+ используется как fallback при недоступности API

## ⚙️ Изменение станций
Настройки → Устройства и службы → Chelyabinsk Air → **Настроить**. Интеграция перезагрузится автоматически; устройства и сенсоры снятых станций удаляются.

## 🧪 Отладка

Для включения логов добавьте в configuration.yaml:
```
logger:
  logs:
    custom_components.chelyabinsk_air: debug
```
## 🎛 Карточка

<details>
<summary>Нажмите, чтобы развернуть</summary>
  
<div align="center">
                  
  ![photo_2026-04-08_13-38-28](https://github.com/user-attachments/assets/ea82606c-a97f-4d6b-b040-adf658f5b824)

</div>

```yaml
type: vertical-stack
cards:
  - type: markdown
    content: |
      ## 🌍 Челябинск — качество воздуха
      📍 ГНС №73, пр. Победы, 198а

  # 🌡️ Погода
  - type: horizontal-stack
    cards:
      - type: gauge
        entity: sensor.cheliabinsk_gns_no73_pr_pobedy_d_198a_temperatura
        name: Температура
        min: -30
        max: 40

      - type: gauge
        entity: sensor.cheliabinsk_gns_no73_pr_pobedy_d_198a_vlazhnost
        name: Влажность
        min: 0
        max: 100

      - type: gauge
        entity: sensor.cheliabinsk_gns_no73_pr_pobedy_d_198a_atmosfernoe_davlenie
        name: Давление
        min: 720
        max: 800

  # 🌬️ Ветер
  - type: entities
    title: 🌬️ Ветер
    entities:
      - entity: sensor.cheliabinsk_gns_no73_pr_pobedy_d_198a_skorost_vetra
        name: Скорость
      - entity: sensor.cheliabinsk_gns_no73_pr_pobedy_d_198a_napravlenie_vetra
        name: Направление (°)

  # ☣️ Газы
  - type: entities
    title: ☣️ Загрязнение воздуха
    show_header_toggle: false
    entities:
      - entity: sensor.cheliabinsk_gns_no73_pr_pobedy_d_198a_ammiak
        name: Аммиак
      - entity: sensor.cheliabinsk_gns_no73_pr_pobedy_d_198a_dioksid_azota
        name: NO₂
      - entity: sensor.cheliabinsk_gns_no73_pr_pobedy_d_198a_oksid_azota
        name: NO
      - entity: sensor.cheliabinsk_gns_no73_pr_pobedy_d_198a_dioksid_sery
        name: SO₂
      - entity: sensor.cheliabinsk_gns_no73_pr_pobedy_d_198a_oksid_ugleroda
        name: CO
      - entity: sensor.cheliabinsk_gns_no73_pr_pobedy_d_198a_serovodorod
        name: H₂S

  # 🌫️ Частицы
  - type: entities
    title: 🌫️ Частицы
    entities:
      - entity: sensor.cheliabinsk_gns_no73_pr_pobedy_d_198a_pm2_5
        name: PM2.5
      - entity: sensor.cheliabinsk_gns_no73_pr_pobedy_d_198a_pm10
        name: PM10
```

</details>

## 🤝 Вклад

Pull requests и идеи приветствуются!

## 📄 Лицензия

MIT
