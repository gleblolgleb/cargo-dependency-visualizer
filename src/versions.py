"""Сравнение SemVer и требований версий Cargo без внешних библиотек."""

import operator
import re

from config import ConfigError, check_version

COMPONENTS = 3
FIRST = 0
SECOND = 1
PATCH = 2
COMPARISONS = {
    ">": operator.gt, ">=": operator.ge,
    "<": operator.lt, "<=": operator.le, "=": operator.eq,
}
CLAUSE = re.compile(r"^(>=|<=|>|<|=|\^|~)?\s*(\S+)$")


class VersionError(ValueError):
    """Некорректная версия или требование Cargo."""


def version_key(value):
    """Вернуть сравнимый ключ SemVer, игнорируя метаданные сборки."""
    try:
        check_version(value)
    except (ConfigError, TypeError) as error:
        raise VersionError(f"Неверная версия: {value}.") from error
    core, _, pre = value.split("+", maxsplit=1)[0].partition("-")
    numbers = tuple(map(int, core.split(".")))
    parts = tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in pre.split(".")
    ) if pre else ()
    return numbers, not bool(pre), parts


def parse_clause(text):
    """Разобрать один компаратор, сокращенную версию или wildcard."""
    match = CLAUSE.fullmatch(text.strip())
    if not match:
        raise VersionError(f"Неверное требование версии: {text}.")
    operation, raw = match.groups()
    core, _, pre = raw.split("+", maxsplit=1)[0].partition("-")
    fields = core.split(".")
    wildcard = any(field in ("*", "x", "X") for field in fields)
    if wildcard:
        return parse_wildcard(operation, fields, pre)
    key = expand_version(fields, pre)
    return operation or "^", key, len(fields)


def expand_version(fields, pre):
    """Дополнить сокращенную версию нулями и проверить SemVer."""
    if len(fields) > COMPONENTS or not all(p.isdigit() for p in fields):
        raise VersionError("Неверные компоненты требования версии.")
    if pre and len(fields) != COMPONENTS:
        raise VersionError("Prerelease требует полную версию.")
    full = fields + ["0"] * (COMPONENTS - len(fields))
    return version_key(".".join(full) + ("-" + pre if pre else ""))


def parse_wildcard(operation, fields, pre):
    """Проверить wildcard и вернуть фиксированную часть версии."""
    if operation or pre or len(fields) > COMPONENTS:
        raise VersionError("Неверное wildcard-требование.")
    fixed = []
    seen = False
    for field in fields:
        if field in ("*", "x", "X"):
            seen = True
        elif seen or not field.isdigit():
            raise VersionError("Неверное wildcard-требование.")
        else:
            fixed.append(field)
    full = fixed + ["0"] * (COMPONENTS - len(fixed))
    return "*", version_key(".".join(full)), len(fixed)


def upper_bound(key, position):
    """Вычислить исключенную верхнюю границу диапазона."""
    values = list(key[FIRST])
    values[position] += 1
    for index in range(position + 1, COMPONENTS):
        values[index] = 0
    return tuple(values), True, ()


def caret_position(numbers, count):
    """Найти компонент, ограничивающий совместимость caret."""
    for index in range(count):
        if numbers[index]:
            return index
    return count - 1


def compare_partial(candidate, operation, bound, count):
    """Сравнить полную или сокращенную версию с компаратором."""
    if count == COMPONENTS:
        return COMPARISONS[operation](candidate, bound)
    left = candidate[FIRST][:count]
    right = bound[FIRST][:count]
    return COMPARISONS[operation](left, right)


def matches_clause(candidate, clause):
    """Проверить один компаратор требования Cargo."""
    operation, bound, count = clause
    if operation in COMPARISONS:
        return compare_partial(candidate, operation, bound, count)
    if operation == "*":
        return candidate[FIRST][:count] == bound[FIRST][:count]
    if operation == "~":
        position = SECOND if count > SECOND else FIRST
    else:
        position = caret_position(bound[FIRST], count)
    return bound <= candidate < upper_bound(bound, position)


def prerelease_allowed(candidate, clauses):
    """Разрешить prerelease только для явно указанного ядра версии."""
    if candidate[SECOND]:
        return True
    return any(
        not bound[SECOND] and bound[FIRST] == candidate[FIRST]
        for _, bound, _ in clauses
    )


def matches_requirement(version, requirement):
    """Проверить все компараторы Cargo, соединенные запятыми."""
    if not isinstance(requirement, str) or not requirement.strip():
        raise VersionError("Пустое требование версии.")
    clauses = [parse_clause(part) for part in requirement.split(",")]
    candidate = version_key(version)
    return prerelease_allowed(candidate, clauses) and all(
        matches_clause(candidate, clause) for clause in clauses
    )
