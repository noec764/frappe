from frappe import _

def get_data():
	return {
		'fieldname': 'payment_gateway',
		'transactions': [
			{
				'label': _('Accounts'),
				'items': ['Payment Gateway Account']
			}
		]
	}
