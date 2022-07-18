from .Action import Action


class _BaseActionRunner():
	def __init__(self):
		...

	def is_action_valid(self, action: Action):
		if (action.local is None) and (action.remote is None):
			# cannot be both None
			return False
		return True

	def run_action(self, action: Action):
		if not self.is_action_valid(action):
			raise ValueError('invalid action')
