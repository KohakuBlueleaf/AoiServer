class request:
	def __init__(self, method, data):
		self.method = method
		self.data = data

	def __getitem__(self, key):
		return getattr(self, key)	

class response:
	def __init__(self, method, data, state='suc'):
		self.method = method
		self.data = data
		self.state = state

	def __getitem__(self, key):
		return getattr(self, key)

class ServerError(Exception):
	pass