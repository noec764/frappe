frappe.tour["Energy Point Settings"] = {
	fr: [
		{
			fieldname: "enabled",
			description: "Active/Désactive l'attribution de points d'énergie",
		},
		{
			fieldname: "review_levels",
			description:
				"Règles d'attribution de points de revue aux utilisateurs en fonction de leurs rôles.<br>Si un utilisateur a plusieurs rôles, le niveau avec nombre de points le plus élevé lui sera attribué.",
		},
		{
			fieldname: "point_allocation_periodicity",
			description: "Périodicité d'allocation des points de revue",
		},
		{
			fieldname: "last_point_allocation_date",
			description:
				"Dernière date d'allocation des points de revue <i>(Géré automatiquement)</i>",
		},
		{
			tour_step_type: "Button",
			button_label: __("Give Review Points"),
			title: __("Give Review Points"),
			description:
				"Outil permettant d'attribuer manuellement des points de revue à un utilisateur",
		},
	],
};
