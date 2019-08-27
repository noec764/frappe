const submitButton = document.querySelector('#submit-button');
const data = {{ frappe.form_dict | json }};

braintree.dropin.create({
	authorization: "{{ client_token }}",
	selector: '#dropin-container',
	threeDSecure: {
		amount: "{{ amount }}",
	},
	paypal: {
		flow: 'vault'
	},
	locale: "{{ locale }}"
}, function(err, instance) {
	if (err) {
		// Handle any errors that might've occurred when creating Drop-in
		processError(err)
		return;
	}
	submitButton.addEventListener('click', function() {
		instance.requestPaymentMethod(function(err, payload) {
			if (err) {
				console.log('Error', err);
				return;
			}

			if (payload.liabilityShifted || payload.type !== 'CreditCard') {
				submitPayment(payload);
			} else {
				dropinInstance.clearSelectedPaymentMethod();
			}
		});
	});

	instance.on('paymentMethodRequestable', function (event) {
		submitButton.removeAttribute('disabled');
	});

	instance.on('noPaymentMethodRequestable', function () {
		submitButton.setAttribute('disabled', true);
	});
});

const submitPayment = payload => {
	frappe.call({
		method: "frappe.templates.pages.integrations.braintree_checkout.make_payment",
		freeze: true,
		headers: { "X-Requested-With": "XMLHttpRequest" },
		args: {
			"payload_nonce": payload.nonce,
			"data": data,
		}
	})
	.then(r => {
		if (r.message && r.message.status == "Completed") {
			window.location.href = r.message.redirect_to
		} else if (r.message && r.message.status == "Error") {
			window.location.href = r.message.redirect_to
		}
	})
}

const processError = error => {
	submitButton.style.display = "none"
	$('#error-msg').html(error.message);
	$('.error').show()
}
