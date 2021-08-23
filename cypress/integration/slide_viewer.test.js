import CypressTestEventDocType from '../fixtures/test_event';

context('Slide View', () => {
	const route1 = '_cypress-test-slide-view1';
	const docsToRemove = [
		['Slide View', route1],
		['DocType', CypressTestEventDocType.name],
	];
	const slideView1 = {
		title: 'Cypress Test Slide View',
		route: route1,
		allow_back: true,
		allow_any: true,
		done_state: true,
		reference_doctype: CypressTestEventDocType.name,
		can_edit_doc: true,
		can_create_doc: true,
	}

	before(() => {
		cy.visit('/login');
		cy.login('Administrator', 'admin');

		cy.insert_doc('DocType', CypressTestEventDocType, true);

		cy.insert_doc('Slide View', slideView1, true);

		cy.visit('/desk');
	});

	it('creates a document with the Slide Viewer', () => {
		cy.visit('/desk/slide-viewer/' + route1);

		// Fill mandatory fields
		cy.fill_field('subject', 'this is a test event', 'Data').blur();

		// Click buttons
		cy.get('.next-btn').should('be.visible').click();
		cy.get('.next-btn').should('be.visible').click();
		cy.get('.complete-btn').should('be.visible').click();

		cy.location('pathname').should('match', /\/app\/cypress-test-event\/__CY\d*$/);

		cy.go_to_list(CypressTestEventDocType.name);
		cy.get('.list-row').should('contain', 'this is a test event');

		cy.go(-1);
		cy.get('body').type('{ctrl}{shift}D{enter}'); // clean-up
	});

	it('allows full page edit even with empty mandatory fields', () => {
		cy.visit('/desk/slide-viewer/' + route1);
		cy.get('.btn-edit-in-full-page').should('be.visible').click(); // click edit in full page
		cy.location('pathname').should('match', /\/app\/cypress-test-event\/new-cypress-test-event-\d*$/); // check url
	});

	it('updates progress dots when changing values', () => {
		cy.visit('/desk/slide-viewer/' + route1);

		// Check progress dots
		cy.get('.slide-step:not(.step-skip)').should('have.length', 3);
		cy.fill_field('event_type', 'Public', 'Select');
		cy.get('.slide-step:not(.step-skip)').should('have.length', 4);
		cy.get(`input[type="checkbox"][data-fieldname="sync_with_google_calendar"]`).click();
		// cy.get_checkbox('sync_with_google_calendar').click();
		cy.get('.slide-step:not(.step-skip)').should('have.length', 5);

		// Fill mandatory fields
		cy.fill_field('subject', 'this is a test event', 'Data').blur();

		// Check that all slides are displayed
		cy.get('.next-btn').should('be.visible').click();
		cy.get('.next-btn').should('be.visible').click();
		cy.get('.next-btn').should('be.visible').click();
		cy.get('.next-btn').should('be.visible').click();
		cy.get('.complete-btn').should('be.visible');
	});

	after(() => {
		for (const doc of docsToRemove) {
			cy.remove_doc(doc[0], doc[1]);
		}
	});
});
