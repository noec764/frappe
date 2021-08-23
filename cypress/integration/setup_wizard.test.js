context('Slide View', () => {
	before(() => {
		cy.visit('/login');
		cy.login('Administrator', 'admin');

		cy.visit('/app/setup-wizard/0');
		cy.get('.slides-wrapper').should('exist');
		cy.wait(300);
		cy.get('#freeze').should('not.exist'); // wait for initial language setup (English)
	});

	it('translate buttons correctly on language change', () => {
		cy.fill_field('language', 'Deutsch', 'Select').blur();
		cy.get('#freeze').should('not.exist');

		cy.get('.next-btn')
			.should('be.enabled')
			.should('contain', 'Weiter');

		cy.fill_field('language', 'Français', 'Select').blur();
		cy.get('#freeze').should('not.exist');

		cy.get('.next-btn')
			.should('be.enabled')
			.should('contain', 'Suivant');

		cy.get('.next-btn').should('be.visible').click();
	});

	it('allows full page edit even with empty mandatory fields', () => {
		cy.fill_field('country', 'États-Unis', 'Select').blur();
		cy.get_field('currency', 'Select').should('have.value', 'USD');

		cy.fill_field('country', 'France', 'Select').blur();
		cy.get_field('currency', 'Select').should('have.value', 'EUR');

		// cy.get('.next-btn').should('be.visible').click();
	});
});
