class DeferredTasks():
	def __init__(self) -> None:
		self._tasks = []

	def __len__(self):
		return len(self._tasks)

	def __bool__(self):
		return bool(self._tasks)

	def push(self, func, *args, **kwargs):
		task = (func, args, kwargs)
		self._tasks.append(task)

	def push_front(self, func, *args, **kwargs):
		task = (func, args, kwargs)
		self._tasks.insert(0, task)

	# def pop(self):
	# 	return self._tasks.pop()

	# def pop_run(self):
	# 	(func, args, kwargs) = self.pop()
	# 	func(*args, **kwargs)
	# 	return (func, args, kwargs)

	# iterator: pop then yield result
	def __iter__(self):
		while self._tasks:
			(func, args, kwargs) = self._tasks.pop()
			yield func(*args, **kwargs)
