import jdatetime
from datetime import datetime
from zoneinfo import ZoneInfo


class PersianText:
    """Centralized Persian number formatting and Jalali datetime helpers."""

    _DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    _locale_set = False

    def __init__(self, timezone_str: str):
        self.timezone = ZoneInfo(timezone_str)
        if not PersianText._locale_set:
            jdatetime.set_locale('fa_IR')
            PersianText._locale_set = True

    def digits(self, text: str | int) -> str:
        return str(text).translate(self._DIGITS)

    def number(self, n: int) -> str:
        return self.digits(n)

    def format_datetime(self, dt: datetime) -> str:
        local = dt.astimezone(self.timezone)
        j = jdatetime.datetime.fromgregorian(datetime=local)
        return self.digits(j.strftime("%H:%M / %d %B"))
