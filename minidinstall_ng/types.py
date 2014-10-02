class StrList:
    def __init__(seperator=',', strip=True):
        self._sep = seperator
        self._strip = strip
    
    def __call__(self, value):
        value = value.split(self._sep)
        if self._strip:
            return map(string.strip, value)

# string list with default configuration
str_list = StrList()

class IntWithBase:
    def __init__(self, base):
        self._base = base
    def __call__(self, value):
        return int(value, self._base)