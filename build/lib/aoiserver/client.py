import os,sys
import socket
from ._client_functions import *
from queue import Queue
from time import sleep
from threading import Thread as Th
import asyncio

class AoiClient:
	class ctx:
		EOF = b'\x00'
		def __init__(self, client):
			self.client = client
		
		def send(self, data):
			send_with_len(self.client, data)
		
		def send_EOF(self):
			self.send(b'\x00')
		
		def recv(self):
			return recv_msg(self.client)

	def __init__(self, unix=False, **setting):
		if unix:
			if 'path' not in setting:
				raise ValueError('path must be setted in unix mode')
			if 'name' not in setting:
				setting['name'] = f"[local_unix:{os.getpid()}]"

			self.client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			self.client.connect(setting['path'])
		else:
			if 'ip' not in setting or 'port' not in setting:
				raise ValueError('ip/port must be setted in tcp mode')
			if 'name' not in setting:
				setting['name'] = f'[{setting["ip"]}:{os.getpid()}]'

			self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.client.connect((setting['ip'], setting['port']))

		self.ctx = AoiClient_an.ctx(self.client)
		self.ctx.send(setting['name'])

		all_request_method = self.ctx.recv()
		for i in all_request_method:
			def func(*args, **kwargs):
				self.ctx.send([i,args,kwargs])
				return self.ctx.recv()
			setattr(self, i, func)
			setattr(self.ctx, i, func)
	
	def transaction(self, func):
		name = func.__name__
		
		def function(*args, **kwargs):
			self.ctx.send([name,None,None])
			return func(self.ctx, *args, **kwargs)
		
		setattr(self, name, function)
		return function


class AoiClient_an:
	class ctx:
		EOF = b'\x00'
		def __init__(self, client):
			self.client = client
		
		def send(self, data):
			send_with_len(self.client, data)
		
		def send_EOF(self):
			self.send(b'\x00')
		
		def recv(self):
			return recv_msg(self.client)

	def __init__(self, unix=False, **setting):
		if unix:
			if 'path' not in setting:
				raise ValueError('path must be setted in unix mode')
			if 'name' not in setting:
				setting['name'] = f"[local_unix:{os.getpid()}]"

			self.client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			self.client.connect(setting['path'])
		else:
			if 'ip' not in setting or 'port' not in setting:
				raise ValueError('ip/port must be setted in tcp mode')
			if 'name' not in setting:
				setting['name'] = f'[{setting["ip"]}:{os.getpid()}]'

			self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.client.connect((setting['ip'], setting['port']))

		self.ctx = AoiClient_an.ctx(self.client)
		self.ctx.send(setting['name'])

		self.handler = lambda data: None
		self.handler_thread = AoiThread(target=self._handle)
		self.handler_thread.start()
	
	def _handle(self):
		while True:
			try:
				data = self.ctx.recv()
			except ConnectionAbortedError:
				break
			self.handler(data)

	def send(self,data):
		self.ctx.send(data)
	
	def recv(self):
		return self.ctx.recv()
	
	def set_handler(self, func):
		self.handler=func
	
	def close(self):
		self.client.close()
		self.handler_thread.stop()


if __name__=='__main__':
	client = AoiClient()
	client.test()