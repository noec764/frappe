from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.data import flt, round_based_on_smallest_currency_fraction


class TestRounding(FrappeTestCase):
	def test_rounding(self):
		self.assertEqual(flt("what"), 0)

		self.assertEqual(flt("0.5", 0), 0)
		self.assertEqual(flt("0.3"), 0.3)

		self.assertEqual(flt("1.5", 0), 2)

		# positive rounding to integers
		self.assertEqual(flt(0.4, 0), 0)
		self.assertEqual(flt(0.5, 0), 0)
		self.assertEqual(flt(1.455, 0), 1)
		self.assertEqual(flt(1.5, 0), 2)

		# negative rounding to integers
		self.assertEqual(flt(-0.5, 0), 0)
		self.assertEqual(flt(-1.5, 0), -2)

		# negative precision i.e. round to nearest 10th
		self.assertEqual(flt(123, -1), 120)
		# self.assertEqual(flt(125, -1), 120)
		self.assertEqual(flt(134.45, -1), 130)
		self.assertEqual(flt(135, -1), 140)

		# positive multiple digit rounding
		# self.assertEqual(flt(1.25, 1), 1.2)
		# self.assertEqual(flt(0.15, 1), 0.2)

		# negative multiple digit rounding
		# self.assertEqual(flt(-1.25, 1), -1.2)
		# self.assertEqual(flt(-0.15, 1), -0.2)

	def round_based_on_smallest_currency_fraction(self):
		# currency rounding
		self.assertEqual(round_based_on_smallest_currency_fraction(0.000, "EUR", 2), 0.00)
		self.assertEqual(round_based_on_smallest_currency_fraction(0.003, "EUR", 2), 0.00)
		self.assertEqual(round_based_on_smallest_currency_fraction(0.005, "EUR", 2), 0.01)
		self.assertEqual(round_based_on_smallest_currency_fraction(0.007, "EUR", 2), 0.01)

		self.assertEqual(round_based_on_smallest_currency_fraction(0.990, "EUR", 2), 0.99)
		self.assertEqual(round_based_on_smallest_currency_fraction(0.993, "EUR", 2), 0.99)
		self.assertEqual(round_based_on_smallest_currency_fraction(0.995, "EUR", 2), 1.00)
		self.assertEqual(round_based_on_smallest_currency_fraction(0.997, "EUR", 2), 1.00)

		self.assertEqual(round_based_on_smallest_currency_fraction(-0.000, "EUR", 2), -0.00)
		self.assertEqual(round_based_on_smallest_currency_fraction(-0.003, "EUR", 2), -0.00)
		self.assertEqual(round_based_on_smallest_currency_fraction(-0.005, "EUR", 2), -0.01)
		self.assertEqual(round_based_on_smallest_currency_fraction(-0.007, "EUR", 2), -0.01)

		self.assertEqual(round_based_on_smallest_currency_fraction(-0.990, "EUR", 2), -0.99)
		self.assertEqual(round_based_on_smallest_currency_fraction(-0.993, "EUR", 2), -0.99)
		self.assertEqual(round_based_on_smallest_currency_fraction(-0.995, "EUR", 2), -1.00)
		self.assertEqual(round_based_on_smallest_currency_fraction(-0.997, "EUR", 2), -1.00)

		# round(2.675, 2) = 2.67, but we want 2.68
		self.assertEqual(round_based_on_smallest_currency_fraction(2.675, "EUR", 2), 2.68)
		self.assertEqual(round_based_on_smallest_currency_fraction(2.675, "EUR", 1), 2.7)

		self.assertEqual(round_based_on_smallest_currency_fraction(-0.54, "EUR", 2), -0.54)
		self.assertEqual(round_based_on_smallest_currency_fraction(-2.54, "EUR", 2), -2.54)
		self.assertEqual(round_based_on_smallest_currency_fraction(-1.230, "EUR", 2), -1.23)
		self.assertEqual(round_based_on_smallest_currency_fraction(-1.235, "EUR", 2), -1.24)
		self.assertEqual(round_based_on_smallest_currency_fraction(-1.239, "EUR", 2), -1.24)
		self.assertEqual(round_based_on_smallest_currency_fraction(-2.230, "EUR", 2), -2.23)
		self.assertEqual(round_based_on_smallest_currency_fraction(-2.235, "EUR", 2), -2.24)
		self.assertEqual(round_based_on_smallest_currency_fraction(-2.239, "EUR", 2), -2.24)

		self.assertEqual(round_based_on_smallest_currency_fraction(0.004999, "EUR", 2), 0.00)
		self.assertEqual(round_based_on_smallest_currency_fraction(-0.004999, "EUR", 2), -0.00)
		self.assertEqual(round_based_on_smallest_currency_fraction(1.004, "EUR", 2), 1.00)
		self.assertEqual(round_based_on_smallest_currency_fraction(-1.004, "EUR", 2), -1.00)
		self.assertEqual(round_based_on_smallest_currency_fraction(1.004999, "EUR", 2), 1.00)
		self.assertEqual(round_based_on_smallest_currency_fraction(-1.004999, "EUR", 2), -1.00)
		self.assertEqual(round_based_on_smallest_currency_fraction(1.005, "EUR", 2), 1.01)
		self.assertEqual(round_based_on_smallest_currency_fraction(-1.005, "EUR", 2), -1.01)

	@given(st.decimals(min_value=-1e9, max_value=1e9, places=2))
	def test_round_currency_does_nothing_if_no_rounding_needed(self, number):
		expected = float(number)
		actual = round_based_on_smallest_currency_fraction(expected, "EUR", 2)
		self.assertEqual(actual, expected)

	@given(
		st.decimals(min_value=-1e9, max_value=1e9, places=2),
		st.decimals(min_value=-9999, max_value=9999),
	)
	def test_round_currency_2(self, base, subunit):
		number = base + (subunit / 10000) / 100
		number = float(number)

		if subunit < 5000:
			expected = float(base)  # round down to nearest cent
		else:
			expected = float(base) + 0.01  # round up to nearest cent

		expected = round(expected, 2)  # remove any floating point artifacts

		actual = round_based_on_smallest_currency_fraction(expected, "EUR", 2)
		self.assertEqual(actual, expected)
