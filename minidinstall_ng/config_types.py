import logging

class StrList:
    def __init__(self, seperator=',', strip=True, type=None):
        self._type = type
        self._sep = seperator
        self._strip = strip
    
    def __call__(self, value):
        value = value.split(self._sep)
        if self._strip:
            value = map(str.strip, value)
        if not self._type is None:
            value = map(self._type)
        return list(value)

def path(value):
    return os.path.normpath(os.path.expanduser(value))

# string list with default configuration
str_list = StrList()

class IntWithBase:
    def __init__(self, base):
        self._base = base
    def __call__(self, value):
        return int(value, self._base)

class Choices:
    def __init__(self, choices):
        self._choices = choices

    def __call__(self, value):
        if not value in self._choices:
            msg = 'value %r is not allowed. Use one of the following: (%s)'
            msg = msg % (value, ', '.join(self._choices))
            raise ValueError(msg)
        return value

def loglevel(value):
    res = None
    try:
        res = logging.__dict__[value.upper()]
    except KeyError:
        pass
    if type(res) != int:
        ValueError("invalid log level %r" % value)
    return res

def str_bool(value):
    if type(value) == str:
        value = value.strip()
        if value.lower() in ('0', 'false', 'no'):
            return False
        return True
    return bool(value)
