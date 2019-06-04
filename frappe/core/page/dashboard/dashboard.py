# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt
from __future__ import unicode_literals
import json
import frappe
from frappe.utils import add_to_date


def cache_source(function):
	def wrapper(*args, **kwargs):
		chart_name = kwargs.get("chart_name")
		cache_key = 'chart-data:{}:{}'.format(frappe.session.user, chart_name)
		if int(kwargs.get("refresh") or 0):
			results = generate_and_cache_results("Dashboard Chart", chart_name, function, cache_key)
		else:
			cached_results = frappe.cache().get_value(cache_key)
			if cached_results:
				results = json.loads(frappe.safe_decode(cached_results))
			else:
				results = generate_and_cache_results("Dashboard Chart", chart_name, function, cache_key)
		return results
	return wrapper

def cache_card_source(function):
	def wrapper(*args, **kwargs):
		card_name = kwargs.get("card_name")
		cache_key = 'card-data:{}:{}'.format(frappe.session.user, card_name)
		if int(kwargs.get("refresh") or 0):
			results = generate_and_cache_results("Dashboard Card", card_name, function, cache_key)
		else:
			cached_results = frappe.cache().get_value(cache_key)
			if cached_results:
				results = json.loads(frappe.safe_decode(cached_results))
			else:
				results = generate_and_cache_results("Dashboard Card", card_name, function, cache_key)
		return results
	return wrapper

def generate_and_cache_results(widget_type, widget_name, function, cache_key):
	results = function(widget_name)
	frappe.cache().set_value(cache_key, json.dumps(results, default=str))
	frappe.db.set_value(widget_type, widget_name, "last_synced_on", frappe.utils.now(), update_modified = False)
	return results

def clear_dashboard_cache(user=None):
	if frappe.flags.in_install:
		return

	cache = frappe.cache()

	if user:
		cache.delete_keys("card-data:{}".format(user))
		cache.delete_keys("chart-data:{}".format(user))
	else:
		cache.delete_keys("card-data")
		cache.delete_keys("chart-data")


def get_from_date_from_timespan(to_date, timespan):
	days = months = years = 0
	if "Last Week" == timespan:
		days = -7
	if "Last Month" == timespan:
		months = -1
	elif "Last Quarter" == timespan:
		months = -3
	elif "Last Year" == timespan:
		years = -1
	return add_to_date(to_date, years=years, months=months, days=days,
		as_datetime=True)