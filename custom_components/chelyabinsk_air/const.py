from datetime import timedelta
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)

DOMAIN = "chelyabinsk_air"
CONF_STATIONS = "stations"

API_URL = "https://emc.gov74.ru/uisem/portal/ad/services/getData.php?d=now&t=chelyabinsk-1"

# Сервер отвечает ~5 минут. Интервал отсчитывается от НАЧАЛА запроса:
# после ответа ждём (TARGET_CYCLE - длительность запроса), минимум MIN_PAUSE.
TARGET_CYCLE = timedelta(minutes=10)
MIN_PAUSE = timedelta(minutes=1)
REQUEST_TIMEOUT = 600  # секунд: медленный ответ — норма для этого API
# Повторяем запрос только если он упал быстро (обрыв, HTML-заглушка),
# долгий таймаут не повторяем — следующий цикл и так скоро.
FAST_FAIL_SECONDS = 60
RETRY_DELAY = 30
# Если запрос завершился менее N секунд назад, повторный не запускаем
RECENT_SECONDS = 45

# Данные станции старше этого срока считаются устаревшими -> сенсор недоступен
MAX_DATA_AGE = timedelta(hours=3)
# Метеоданные приходят раз в 6 часов; более старые строки не используем
METEO_MAX_AGE = timedelta(hours=12)
LOCAL_TZ = ZoneInfo("Asia/Yekaterinburg")  # время в поле "dt" ответа

# Значения ниже порога — служебные «нет данных» (-32768, -9999 и т.п.)
INVALID_VALUE_THRESHOLD = -9999
# Правдоподобный диапазон давления, мм рт. ст.
PRESSURE_RANGE_MMHG = (680, 800)

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_data"
UPDATED_KEY = "_updated"
METEO_DT_KEY = "_meteo_dt"
API_DEVICE_ID = "api"

_M = SensorStateClass.MEASUREMENT

# Загрязнители в API — стандартный индекс (СИ = концентрация / ПДК м.р.),
# безразмерная величина: 1.0 = ровно ПДК, больше 1 — превышение.
METEO_KEYS = {"temperature", "humidity", "wind_speed", "pressure", "wind_dir"}

# key: (название, единица, device_class, state_class)
SENSORS = {
    "ammonia": ("Аммиак", None, None, _M),
    "no2": ("Диоксид азота", None, None, _M),
    "so2": ("Диоксид серы", None, None, _M),
    "no": ("Оксид азота", None, None, _M),
    "co": ("Оксид углерода", None, None, _M),
    "h2s": ("Сероводород", None, None, _M),
    "temperature": ("Температура", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, _M),
    "humidity": ("Влажность", PERCENTAGE, SensorDeviceClass.HUMIDITY, _M),
    "wind_speed": ("Скорость ветра", UnitOfSpeed.METERS_PER_SECOND, SensorDeviceClass.WIND_SPEED, _M),
    "pressure": ("Атмосферное давление", UnitOfPressure.MMHG, SensorDeviceClass.PRESSURE, _M),
    "wind_dir": ("Направление ветра", DEGREE, SensorDeviceClass.WIND_DIRECTION, SensorStateClass.MEASUREMENT_ANGLE),
    "pm25": ("PM2.5", None, None, _M),
    "pm10": ("PM10", None, None, _M),
    "o3": ("Озон", None, None, _M),
    "formaldehyde": ("Формальдегид", None, None, _M),
    "max_si": ("Наибольший СИ", None, None, _M),
}

SENSOR_MAP = {
    "Аммиак": "ammonia",
    "Диоксид азота": "no2",
    "Диоксид серы": "so2",
    "Оксид азота": "no",
    "Оксид углерода": "co",
    "Сероводород": "h2s",
    "Озон": "o3",
    "Формальдегид": "formaldehyde",
    "Частицы 2.5 мкм": "pm25",
    "Частицы 10 мкм": "pm10",
    "Температура": "temperature",
    "Скорость ветра": "wind_speed",
    "Влажность отн.": "humidity",
    "Давление": "pressure",
    "Направление ветра": "wind_dir",
}

STATIONS = {
    "74030116": "Челябинск (ГНС №66, ул. Новороссийская, 8а)",
    "74030117": "Челябинск (ГНС №67, ул. Румянцева, 28а)",
    "74030120": "Челябинск (ГНС №70, ул. Горького, 79)",
    "74030122": "Челябинск (ГНС №72, ул. Трудовая, 35)",
    "74030123": "Челябинск (ГНС №73, пр. Победы, 198а)",

    "74040101": "Челябинск (ТСН №1, ул. Мамина 19б)",
    "74040102": "Челябинск (ТСН №2, пр. Победы 287)",
    "74040103": "Челябинск (ТСН №3, ул. 5-ая Электровозная 5)",
    "74040104": "Челябинск (ТСН №4, ул. Зальцмана 25а)",
    "74040105": "Челябинск (ТСН №5, ул. Кузнецова 51)",
    "74040106": "Челябинск (ТСН №6, ул. Пирогова 1Г/1)",
    "74040107": "Челябинск (ТСН №7, ул. Агаповская 6/1)",
    "74040108": "Челябинск (ТСН №8, ул. Шагольская кв.1 д.6В)",
    "74040109": "Челябинск (ТСН №9, ул. Чичерина 22)",
    "74040110": "Челябинск (ТСН №10, ул. Мраморная 16)",
    "74040111": "Челябинск (ТСН №11, ул. Южный бульвар 35)",
    "74040112": "Челябинск (ТСН №12, пр. Ленина 89Б)",
    "74040113": "Челябинск (ТСН №13, ул. Аральская 21)",
    "74040114": "Челябинск (ТСН №14, ул. Бахчисарайская)",
    "74040115": "Челябинск (ТСН №15, аэропорт, Уйская улица)",
    "74040121": "Челябинск (ТСН №21, ул. Чайковского 1)",
    "74040122": "Челябинск (ТСН №22, ул. Российская 10б)",
    "74040123": "Челябинск (ТСН №23, ул. Машиностроителей 27)",
    "74040124": "Челябинск (ТСН №24, пр. Комсомольский 5)",
    "74040125": "Челябинск (ТСН №25, ул. Новороссийская 63)",
    "74040126": "Челябинск (ТСН №26, ул. Механическая 65)",
    "74040127": "Челябинск (ТСН №27, ул. Калинина 21)",
    "74040128": "Челябинск (ТСН №28, пр. Ленина 57)",
    "74040129": "Челябинск (ТСН №29, ул. Хлебозаводская 1)",
    "74040130": "Челябинск (ТСН №30, ул. Индивидуальная 87/1)",
    "74040140": "Челябинск (ТСН №40, Российская 1 стр.25)",
}