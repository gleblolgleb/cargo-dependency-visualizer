# Практическая работа № 2. Вариант 27

## Этап 4. Дополнительные операции

Приложение строит граф зависимостей с учетом транзитивности.
Обход выполняется алгоритмом DFS без рекурсии, с явным стеком.
Циклические зависимости и петли сохраняются в графе и не приводят
к бесконечному обходу. Каждый узел обрабатывается один раз.

Реализованы два источника: реальный HTTP-индекс Cargo и файл
тестового репозитория с именами пакетов из больших латинских букв.
Используется стандартная библиотека Python 3.9 или новее.
Менеджеры пакетов и сторонние библиотеки получения зависимостей
не используются. Установка зависимостей и сборка не требуются.

## Обратные зависимости: этап 4

Требования этапа: вывести пакеты, зависящие от заданного пакета,
использовать обход предыдущего этапа и продемонстрировать разные случаи
на тестовом репозитории.

В JSON-конфигурацию добавляется `reverse_package`. Например:

```json
{
  "package": "A",
  "repository": "chain-repository.json",
  "test_mode": true,
  "version": "1.0.0",
  "output": "graph.svg",
  "reverse_package": "C"
}
```

Без этого поля сохраняется вывод графа этапа 3.
При наличии поля выводятся все прямые и транзитивные потребители.
Ребра исходного графа переворачиваются, затем вызывается неизмененный
`build_graph` из этапа 3: итеративный DFS с явным стеком.
Каждый потребитель выводится один раз. Искомый пакет не включается
в собственный список потребителей даже при цикле или петле.

В тестовом режиме поиск охватывает весь файл репозитория, включая
пакеты, недостижимые из `package`. В этом режиме `package` сохраняется
как обязательный параметр, но область обратного поиска не ограничивает.
В HTTP-режиме область — граф зависимостей указанного корня `package`
и его версии. Потребители вне этого графа не ищутся по всему Cargo-индексу.
Искомый Cargo-узел задается как `имя@версия`, например `serde@1.0.210`,
и должен присутствовать в построенном графе.

Примеры запуска в Windows:

```bat
run.bat examples\reverse-chain-config.json
run.bat examples\reverse-diamond-config.json
run.bat examples\reverse-cycle-config.json
run.bat examples\reverse-self-loop-config.json
run.bat examples\reverse-isolated-config.json
```

Linux/macOS: `sh run.sh examples/reverse-chain-config.json`
и аналогично для остальных конфигураций.

| Конфигурация | Запрос | Потребители в порядке DFS |
| --- | --- | --- |
| `reverse-chain-config.json` | `C` | `B`, `A` |
| `reverse-diamond-config.json` | `D` | `B`, `A`, `C` |
| `reverse-cycle-config.json` | `A` | `C`, `B` |
| `reverse-self-loop-config.json` | `A` | Нет |
| `reverse-isolated-config.json` | `A` | Нет |

Вывод для цепочки:

```text
Обратные зависимости C:
B
A
```

Если потребителей нет, после заголовка выводится `Нет.`.
Отсутствие самого искомого пакета является ошибкой, код завершения — 2.
Неверный тип, пустая строка и пробелы по краям `reverse_package`
также отклоняются. Изображения на этапе 4 не создаются.

`src/reverse.py`:

- `reverse_dependencies(graph, target)` — обратный граф и обход через DFS;
- `find_target(graph, value, test_mode)` — проверка искомого узла.

Тесты этапа 4 проверяют прямых и транзитивных потребителей, циклы,
петлю, общую зависимость, отсутствие потребителей и пакета, разные версии,
другую компоненту графа и цепочку глубже лимита рекурсии.
Сохранены все файлы тестов предыдущего этапа, включая `test_registry.py`.

## Структура

```text
.gitignore
README.md
config.json
run.bat
run.sh
src/
    main.py
    config.py
    registry.py
    cargo.py
    versions.py
    graph.py
    reverse.py
tests/
    test_config.py
    test_cargo.py
    test_registry.py
    test_versions.py
    test_graph.py
    test_reverse.py
examples/
    chain-config.json
    chain-repository.json
    diamond-config.json
    diamond-repository.json
    cycle-config.json
    cycle-repository.json
    self-loop-config.json
    self-loop-repository.json
    isolated-config.json
    isolated-repository.json
    reverse-chain-config.json
    reverse-diamond-config.json
    reverse-cycle-config.json
    reverse-self-loop-config.json
    reverse-isolated-config.json
```

## Запуск и тесты

Команды выполняются из корня проекта.

Windows:

```bat
run.bat examples\chain-config.json
py -3 src/main.py examples\cycle-config.json
py -3 -m unittest discover -s tests -v
```

Linux/macOS:

```sh
sh run.sh examples/chain-config.json
python3 src/main.py examples/cycle-config.json
python3 -m unittest discover -s tests -v
```

Для HTTP-режима передайте `config.json` вместо конфигурации примера.
При необходимости интерпретатор в скриптах задается через `PYTHON_EXE`.
Справка: `python3 src/main.py --help` (Windows: `py -3`).
Тесты работают без внешней сети, используя также локальный HTTP-сервер.

## Настройки

Единственный аргумент CLI — путь к JSON-конфигурации в UTF-8.
Относительный путь к ней отсчитывается от рабочего каталога.
Пять обязательных параметров сохраняются с первого этапа.
Добавлен необязательный параметр `reverse_package` (строка).

| Поле | Тип | Назначение |
| --- | --- | --- |
| `package` | строка | Корневой пакет графа |
| `repository` | строка | HTTP(S)-адрес индекса или путь тестового файла |
| `test_mode` | логическое | Выбор файла при `true`, HTTP при `false` |
| `version` | строка | Точная версия корневого Cargo-пакета |
| `output` | строка | Имя будущего SVG-файла |

В тестовом режиме имена пакетов состоят только из букв `A-Z`.
`version` сохраняется и проверяется как SemVer, но версии абстрактным
тестовым пакетам не назначаются. Файл `output` на этапе 3 не создается.
Для него требуется расширение `.svg` и существующий родительский каталог.
Пути `repository` в тестовом режиме и `output` отсчитываются от каталога
конфигурации. Режим обратного поиска включается параметром `reverse_package`.

## Формат тестового репозитория

Файл UTF-8 содержит объект JSON: имя пакета сопоставлено списку
его прямых зависимостей. Каждый упомянутый пакет должен быть описан явно.
Например, `chain-repository.json`:

```json
{
  "A": ["B"],
  "B": ["C"],
  "C": []
}
```

Файл `chain-config.json` в том же каталоге:

```json
{
  "package": "A",
  "repository": "chain-repository.json",
  "test_mode": true,
  "version": "1.0.0",
  "output": "graph.svg"
}
```

Пустой список означает отсутствие зависимостей.
Обход включает только вершины, достижимые из выбранного корня.

## Демонстрация разных случаев

Для каждого случая передайте соответствующий файл из `examples`:
`sh run.sh examples/chain-config.json` или
`run.bat examples\chain-config.json`.

Цепочка, `chain-config.json`:

```text
A -> B
B -> C
C -> (нет зависимостей)
```

Общая зависимость, `diamond-config.json`:

```text
A -> B, C
B -> D
D -> (нет зависимостей)
C -> D
```

Цикл, `cycle-config.json`:

```text
A -> B
B -> C
C -> A
```

Петля, `self-loop-config.json`:

```text
A -> A
```

Изолированный корень, `isolated-config.json`:

```text
A -> (нет зависимостей)
```

В последнем репозитории также есть `B -> C`, но эта компонента
недостижима из `A` и в результат не входит.
Все пять примеров дополнительно проверяются автоматическими тестами.

## Реальный индекс Cargo

При `test_mode=false` используется базовый URL HTTP(S) sparse-индекса,
например `https://index.crates.io`, без префикса `sparse+`.
Адрес страницы пакета или Git-репозитория вместо индекса не подходит.
Точная версия корня берется из `version`. Узел обозначается `имя@версия`:
разные версии одного пакета являются разными вершинами.

Для каждого ребра выбирается максимальная неотозванная (`yanked=false`)
версия, удовлетворяющая `req`. Поддержаны caret, tilde, wildcard,
компараторы и их сочетания через запятую, правила prerelease и SemVer.
Переименования учитываются через поле `package`.
Индекс каждого пакета загружается один раз за запуск.

Как и на этапе 2, рассматриваются все объявленные зависимости:
`normal`, `build`, `dev`, optional и зависимости отдельных платформ.
Повторяющиеся ребра между одной парой вершин объединяются.
Это граф объявленных зависимостей; настройки features и платформы
не выбираются. Глобальное согласование версий как в Cargo.lock
не выполняется: подходящая версия выбирается независимо для каждого ребра.
Зависимости из другого индекса явно отклоняются.

Сведения о формате и версиях:
[индекс Cargo](https://doc.rust-lang.org/cargo/reference/registry-index.html),
[требования версий](https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html).

## Ошибки

При успехе код завершения — 0, при ошибке — 2.
Ошибка выводится в stderr без частичного результата и traceback.
Обрабатываются ошибки JSON и параметров, недопустимые имена тестовых
пакетов, неверные списки зависимостей, ссылки на отсутствующие пакеты,
отсутствие корня, сетевые ошибки и тайм-аут (20 секунд), неверный индекс,
отсутствие запрошенной или подходящей версии и неверные требования версий.

## Функции

`src/main.py`:

- `node_label(node)` — представление имени узла;
- `get_graph(config, filename)` — выбор источника и запуск обхода;
- `format_result(config, graph)` — подготовка вывода выбранного режима;
- `main()` — аргументы CLI, обработка ошибок и вывод результата.

`src/graph.py`:

- `build_graph(root, children)` — DFS с явным стеком без рекурсии;
- `validate_test_graph(graph)` — проверка имен и ссылок тестового графа;
- `read_test_repository(config, filename)` — чтение всего тестового файла;
- `load_test_graph(config, filename)` — чтение файла и построение графа.

`src/cargo.py`:

- `parse_index(text, package)` — разбор записей версий из индекса;
- `dependency_name(dependency)` — имя с учетом переименования;
- `check_registry(dependency, repository)` — проверка источника зависимости;
- `CargoSource.__init__(repository)` — создание поставщика данных и кеша;
- `CargoSource.records(package)` — получение записей с кешированием;
- `CargoSource.entry(node)` — поиск точной версии узла;
- `CargoSource.resolve(dependency)` — выбор подходящей версии;
- `CargoSource.children(node)` — список узлов прямых зависимостей.

`src/registry.py`:

- `index_path(package)` — вычисление пути Cargo-пакета;
- `download_index(repository, package)` — HTTP-загрузка индекса пакета;
- `validate_dependencies(entry)` — проверка списка прямых зависимостей.

`src/versions.py`:

- `version_key(value)` — ключ для сравнения SemVer;
- `parse_clause(text)` — разбор одного компаратора;
- `expand_version(fields, pre)` — дополнение сокращенной версии;
- `parse_wildcard(operation, fields, pre)` — разбор wildcard;
- `upper_bound(key, position)` — верхняя граница диапазона;
- `caret_position(numbers, count)` — граница совместимости caret;
- `compare_partial(candidate, operation, bound, count)` — сравнение версий;
- `matches_clause(candidate, clause)` — проверка одного компаратора;
- `prerelease_allowed(candidate, clauses)` — допуск prerelease;
- `matches_requirement(version, requirement)` — проверка требования Cargo.

`src/config.py`:

- `read_json(path)` — чтение объекта JSON;
- `check_field(name, value)` — проверка типа и базовых ограничений поля;
- `check_fields(data)` — проверка состава настроек;
- `local_path(value, base)` — путь относительно конфигурации;
- `check_repository(data, base)` — проверка URL или тестового файла;
- `check_output(value, base)` — проверка имени будущего SVG;
- `check_version(value)` — проверка версии SemVer;
- `load_config(filename)` — общая загрузка и проверка настроек.

Классы `ConfigError`, `RegistryError`, `GraphError` и `VersionError`
представляют ошибки соответствующих частей приложения.
