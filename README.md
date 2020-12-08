# Телеметрия в эксперименте СФЕРА-2

## База данных телеметрии. Пакет `telemetry_querying`

Данные телеметрии были аккумулированы из разных источников, вычищены, дополнены и загружены в базу MongoDB. Пока есть только данные о телеметрии **установки**, наземная телеметрия — TBD.

`telemetry_querying` — пакет с некоторыми удобными методами работы с базой. Помимо этого пакета, можно обращаться к ней и напрямую, например через CLI `mongo`, но по крайней мере для экспорта данных в текстовые файлы удобно использовать Python-интерфейс.

### Функции работы с базой

#### `interpolate_field`: значение любого поля в произвольный момент времени

```python
from datetime import datetime
from telemetry_querying import interpolate_field

dt = datetime.strptime("2013-03-14 08:36:06", r"%Y-%m-%d %X")
H = interpolate_field('H_m', dt)  # by default performs linear interpolation

dt = datetime.strptime("2012-03-14 08:36:06", r"%Y-%m-%d %X")
H = interpolate_field('H_m', dt, kind='nearest')  # just return closest value
```

Названия полей (есть недосмотр: поля для `Tbot_C` и `Ttop_C` кое-где не переименованы, в запросах по ним могут быть ошибки):

```python
from telemetry_querying import all_field_names
print(all_field_names)
```

### Доступ к базе

На текущий момент работа с базой данных телеметрии возможна только локально, для этого нужно:

1. [Скачать, установить и запустить](https://docs.mongodb.com/manual/installation/#mongodb-community-edition-installation-tutorials) сервер MongoDB Community Edition для нужной платформы.

    1a. [Скачать](https://www.mongodb.com/try/download/database-tools) MongoDB Database Tools, если они не установлены вместе с сервером (на Windows нужно устанавливать отдельно, на Linux — нет)

2. [Скачать](https://drive.google.com/file/d/1z9shxr1YIpbffB45a05nW_UU-JzTjCO5/view?usp=sharing) дамп данных базы (бинарный формат)

3. Загрузить данные из дампа в уже запущенный сервер с помощью mongorestore (часть Database Tools):

    ```bash
    mongorestore "path/to/unzipped/dump"
    ```

4. Готово! Можно делать запросы к базе через CLI `mongo` или GUI-клиент (я использую [Robo 3T](https://robomongo.org/)). Пример использования `mongo` для выполнения запроса записей телеметрии за первую минуту девятого часа утра 13 марта 2013 (UTC) (запрос должен вернуть 17 документов):

    ```javascript
    > use sphere_telemetry
    > db.master.find({utc_dt: {$gt: new Date("2013-03-13T08:00:01Z"), $lt: new Date("2013-03-13T08:01:01Z")}})
    ```

    Наример первый документ по этому запросу должен выглядеть так:

    ```javascript
    {
        "_id" : ObjectId("5f67f1f156bcf2938d672e65"),  // unique ID generated by MongoDB
        "utc_dt" : ISODate("2013-03-13T08:00:04.000Z"),  // Z at the end stands for UTC time!
        "Clin1" : -0.5, "Clin2" : 0.3, "Clin_theta" : 0.6, "E_lon" : 10423.3358, "HDOP" : 0.9, "H_m" : 449.0,
        "I" : 0.94, "I_code" : 64, "Led_ch0" : 3419, "Led_ch1" : 0, "Led_ch2" : 3412, "Led_ch3" : 2557,
        "N_lat" : 5147.8066, "Nsat" : 9, "P0_code" : 42679, "P0_hPa" : 968.4, "P1_code" : 40127, "P1_hPa" : 966.2,
        "T0_C" : 24.9, "T0_code" : 35810, "T1_C" : -4.7, "T1_code" : 31953, "Tm_C" : -3.75, "Tp_C" : 29.25,
        "U15" : 14.97, "U5" : 5.16, "Uac" : 18.46, "compass" : 265.6,
        "from_onboard" : true,
        "source_id" : 3
    }
    ```

MongoDB — документоориентированная БД, поэтому каждая запись хранится в формате, повторяющим синтаксис JSON. Поля со значениями NaN и другими невалидными значениями были исключены, поэтому если в конкретной записи в логе не было, например, поля `T1_code`, то в соответствующем документе также просто не будет такого ключа. Для выбора только документов-записей с нужным полем можно сделать запрос:

```javascript
> db.master.find({compass: {$exists: true}})  // find all records with compass data
```

Чтобы не терять информацию об источнике той или иной записи в базе, использована следующая конвенция: в каждом документе хранится булевый флаг `from_onboard: true` или `from_datum: true`, указывающий источник данных, а также целое число `source_id`, указывающее файл-происхождение записи. Получить файл по значению `source_id` можно в отдельной вспомогательной коллекции `sources`. Запросы для получения имен файлов текстовых логов и таблиц-датумов:

```javascript
> db.sources.find({name: "onboard_logs"})
> db.sources.find({name: "datum_tables"})
```

Пример запроса с использованием [агрегационного пайплайна](https://docs.mongodb.com/manual/aggregation/) MongoDB, который выбирает из записей только те, в которых есть показания компаса, а затем форматирует выдачу, возвращая записи без лишних полей — база при этом не изменяется, только отображается в более удобном для пользователя виде.

```javascript
> db.master.aggregate([
.     {$match: {compass: {$exists: true}}},
.     {$project: {utc_dt: true, compass: true}}
. ])
```

## Работа с сырыми данными, ETL

Эти скрипты хранятся по большей части для истории, все новые операции следует проводить с помощью базы Mongo.

### `sphere_log_parser`

— пакет для парсинга файлов логов в форматах эксперимента СФЕРА-2.

Импорт и стандартное использование:

```python
import sphere_log_parser as slp
df = slp.read_log_to_dataframe(filename, parsing_config=slp.GROUND_DATA_CONFIG, logging=True)
```

Описание пакета и способы добавления полей данных и конфигов:

```python
help(slp)
```

### `heigh_correction`

— пакет для коррекции показаний GPS-датчика высоты по данным барометра

Глобальный импорт как пакета пока не настроен, можно работать вручную через `main.py`

### `inclinometer_fetching_2012_logs.ipynb`

— небольшой ноутбук, в котором производится (неудачная) попытка собрать данные инклинометра в полётах за 2012 год

### [DEPRECATED, см. `telemetry_qurying`] `datum_querying.py`

— модуль для получения данных в определённые моменты времени из датумов. Для использования необходимо указать в модуле папку, где лежат посекундные датумы для требуемых годов. Пример запроса:

```python
from datum_querying import telemetry_data_at
df = telemetry_data_at(
    [
        '2013-03-15 12:00:00',
        '2012-03-15',
        '2011-03-15T15',
    ],
    columns=['H', 'N', 'E']
)
```

**Информация в датумах не полна, включены только логи с бортового компьютера, следует использовать базу Mongo, где агрегирована вся телеметрия**

### Пакет `telemetry_etl`

— скрипты для чтения данных телеметрии из текстовых логов и датума и записи в базу данных Mongo. Запускать самостоятельно не требуется, лежат для информации и истории.

### `local_to_utc_conversion.ipynb`

— ноутбук для исследования возможности перевести дату-время, распарсенную из текстовых логов, в UTC. Время в UTC хранится в виде 6-значного числа (GPS timestamp), а дату нужно разметить вручную.
