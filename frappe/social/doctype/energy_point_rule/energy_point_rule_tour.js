frappe.tour["Energy Point Rule"] = {
	fr: [
		{
			fieldname: "enabled",
			description: "Active/Désactive la règle d'attribution de points d'énergie",
		},
		{
			fieldname: "reference_doctype",
			description: "Type de document de référence déclenchant la règle.",
		},
		{
			fieldname: "for_doc_event",
			description:
				"Evénement permettant le déclenchement de la règle.<br><i>Ex. <strong>Nouveau</strong>: La création d'un nouveau document déclenche l'attribution de points.</i>",
		},
		{
			fieldname: "for_assigned_users",
			description:
				"La règle attribuera les points aux utilisateurs assignés au document déclencheur",
		},
		{
			fieldname: "points",
			description: "Nombre de points attribués",
		},
		{
			fieldname: "user_field",
			description:
				"Champ contenant la référence de l'utilisateur à qui attribuer les points",
		},
		{
			fieldname: "multiplier_field",
			description:
				"Champ contenant un nombre entier ou réel permettant de multiplier le nombre de points à attribuer",
		},
		{
			fieldname: "apply_only_once",
			description:
				"Option permettant de n'appliquer la règle qu'une seule fois pour chaque document",
		},
		{
			fieldname: "condition",
			description:
				"Condition permettant de filtrer les documents déclenchant l'attribution de points",
		},
	],
};
