from typing import Optional

def maybe_int(v: Optional[str]) -> Optional[int]:
	if isinstance(v, str):
		return int(v)
	return None


def set_flag(doc):
	doc.flags.nextcloud_triggered_update = True


def check_flag(doc):
	return doc.flags.nextcloud_triggered_update
