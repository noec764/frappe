"""
Why are these functions needed?
Both in frappe and in this module, we use datetime objects.
We assume that these datetime objects are:
- in the local timezone
- offset-naive (with no timezone information, .tzinfo is None)
"""

from functools import lru_cache
from frappe.utils import get_time_zone  # type: ignore
from datetime import datetime


@lru_cache(maxsize=None)
def get_local_tzinfo():
	from pytz import timezone
	return timezone(get_time_zone())


def set_timezone_to_local(dt: datetime):
	"""
	Remove the timezone information (.tzinfo = None),
	effectively creating an offset-naive datetime object,
	which is assumed everywhere in frappe to be in the local timezone.

	Args:
		dt (datetime): A datetime object, whose values are assumed to be in the local timezone, and whose tzinfo property does not matter.

	Returns:
		datetime: A datetime object, whose values are in the local timezone, and whose tzinfo property is None.
	"""
	return dt.replace(tzinfo=None)


def convert_local_time_to_utc(dt: datetime):
	if not dt.tzinfo:
		tzinfo = get_local_tzinfo()
		dt = tzinfo.localize(dt)
	return dt.astimezone(None).replace(tzinfo=None)


def convert_utc_to_local_time(dt: datetime):
	"""
	Convert a UTC datetime object to a local datetime object.
	The date/time values are updated according to the offset of the local timezone.

	The timezone information is stripped from the datetime object, making it offset-naive.
	Offset-naive datetime objects are assumed everywhere in frappe to be in the local timezone.

	Args:
		dt (datetime): A datetime object, whose values are assumed to be in UTC, and whose tzinfo property does not matter.

	Returns:
		datetime: A datetime object, whose values are in the local timezone, and whose tzinfo property is None.

	Example:
		>>> from datetime import datetime
		>>> dt = datetime(2021, 1, 1, 9, 0, 0)  # 9:00 UTC
		>>> dt
		datetime.datetime(2021, 1, 1, 9, 0, 0)
		>>> frappe.utils.get_time_zone()
		'Asia/Kolkata'
		>>> convert_utc_to_local_time(dt)  # 9:00 UTC -> 14:30 UTC+5:30
		datetime.datetime(2021, 1, 1, 14, 30, 0)
	"""
	tzinfo = get_local_tzinfo()
	return dt.astimezone(tzinfo).replace(tzinfo=None)

def strip_datetime_milliseconds(dt: datetime):
	return dt.replace(microsecond=0)
