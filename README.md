# Телеметрия в эксперименте СФЕРА-2

## sphere_log_parser
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