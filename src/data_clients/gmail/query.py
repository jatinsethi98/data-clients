"""Gmail search query builder."""

from typing import List, Union


def construct_query(*query_dicts, **query_terms) -> str:
    """
    Constructs a Gmail search query from either:

    (1) A list of dictionaries representing queries to "or" (only one of the
        queries needs to match).

    (2) Keyword arguments specifying individual query terms (each keyword will
        be and'd).

    To negate any term, use "exclude_<keyword>" instead of "<keyword>".

    For non-boolean values, use a tuple () for AND or a list [] for OR.

    Keyword Arguments:
        sender, recipient, subject, labels, attachment, spec_attachment,
        exact_phrase, cc, bcc, before, after, older_than, newer_than,
        near_words, starred, snoozed, unread, read, important, drive,
        docs, sheets, slides, list, in, delivered_to, category, larger,
        smaller, id, has
    """
    if query_dicts:
        return _or([construct_query(**query) for query in query_dicts])

    terms = []
    for key, val in query_terms.items():
        exclude = False
        if key.startswith('exclude'):
            exclude = True
            key = key[len('exclude_'):]

        query_fn = globals()[f"_{key}"]
        conjunction = _and if isinstance(val, tuple) else _or

        if key in ['newer_than', 'older_than', 'near_words']:
            if isinstance(val[0], (tuple, list)):
                term = conjunction([query_fn(*v) for v in val])
            else:
                term = query_fn(*val)

        elif key == 'labels':
            if isinstance(val[0], (tuple, list)):
                term = conjunction([query_fn(labels) for labels in val])
            else:
                term = query_fn(val)

        elif isinstance(val, (tuple, list)):
            term = conjunction([query_fn(v) for v in val])

        else:
            term = query_fn(val) if not isinstance(val, bool) else query_fn()

        if exclude:
            term = _exclude(term)

        terms.append(term)

    return _and(terms)


def _and(queries: List[str]) -> str:
    if len(queries) == 1:
        return queries[0]
    return f'({" ".join(queries)})'


def _or(queries: List[str]) -> str:
    if len(queries) == 1:
        return queries[0]
    return '{' + ' '.join(queries) + '}'


def _exclude(term: str) -> str:
    return f'-{term}'


def _sender(sender: str) -> str:
    return f'from:{sender}'


def _recipient(recipient: str) -> str:
    return f'to:{recipient}'


def _subject(subject: str) -> str:
    return f'subject:{subject}'


def _labels(labels: Union[List[str], str]) -> str:
    if isinstance(labels, str):
        return _label(labels)
    return _and([_label(label) for label in labels])


def _label(label: str) -> str:
    return f'label:{label}'


def _spec_attachment(name_or_type: str) -> str:
    return f'filename:{name_or_type}'


def _exact_phrase(phrase: str) -> str:
    return f'"{phrase}"'


def _starred() -> str:
    return 'is:starred'


def _snoozed() -> str:
    return 'is:snoozed'


def _unread() -> str:
    return 'is:unread'


def _read() -> str:
    return 'is:read'


def _important() -> str:
    return 'is:important'


def _cc(recipient: str) -> str:
    return f'cc:{recipient}'


def _bcc(recipient: str) -> str:
    return f'bcc:{recipient}'


def _after(date: str) -> str:
    return f'after:{date}'


def _before(date: str) -> str:
    return f'before:{date}'


def _older_than(number: int, unit: str) -> str:
    return f'older_than:{number}{unit[0]}'


def _newer_than(number: int, unit: str) -> str:
    return f'newer_than:{number}{unit[0]}'


def _near_words(
    first: str,
    second: str,
    distance: int,
    exact: bool = False,
) -> str:
    query = f'{first} AROUND {distance} {second}'
    if exact:
        query = '"' + query + '"'
    return query


def _attachment() -> str:
    return 'has:attachment'


def _drive() -> str:
    return 'has:drive'


def _docs() -> str:
    return 'has:document'


def _sheets() -> str:
    return 'has:spreadsheet'


def _slides() -> str:
    return 'has:presentation'


def _list(list_name: str) -> str:
    return f'list:{list_name}'


def _in(folder_name: str) -> str:
    return f'in:{folder_name}'


def _delivered_to(address: str) -> str:
    return f'deliveredto:{address}'


def _category(category: str) -> str:
    return f'category:{category}'


def _larger(size: str) -> str:
    return f'larger:{size}'


def _smaller(size: str) -> str:
    return f'smaller:{size}'


def _id(message_id: str) -> str:
    return f'rfc822msgid:{message_id}'


def _has(attribute: str) -> str:
    return f'has:{attribute}'
