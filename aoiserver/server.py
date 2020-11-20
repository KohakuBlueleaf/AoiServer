import socket,asyncio
import os,sys
import json
from time import time,ctime
from traceback import format_exc
from ._server_functions import recv,send


class AoiServer:
	class ctx:
		EOF = b'\x00'
		def __init__(self, writer, reader, peername):
			self.writer = writer
			self.reader = reader
			self.name = peername
		
		async def send(self, data):
			await send(self.writer, data)
		
		async def send_EOF(self):
			await self.send(b'\x00')
		
		async def recv(self):
			return await recv(self.reader)

	def __init__(self, unix=False, **setting):
		self.loop = asyncio.get_event_loop()
		self._handler = {}
		self._transaction = {}
		self.all_context = {}

		if unix:
			if 'path' not in setting:
				raise ValueError('path must be setted in unix mode')
			self.loop.create_task(asyncio.start_unix_server(self._handle_client, setting['path']))
		else:
			if 'ip' not in setting or 'port' not in setting:
				raise ValueError('ip/port must be setted in tcp mode')
			self.loop.create_task(asyncio.start_server(self._handle_client, setting['ip'], setting['port']))
	
	def run(self):
		print('Server Start')
		self.loop.run_forever()

	def request_handler(self, func):
		self._handler[func.__name__] = func
		
	def transaction(self, func):
		self._transaction[func.__name__] = func

	async def _handle_client(self,reader,writer):
		peername = await recv(reader)

		ctx = self.ctx(writer, reader, peername)
		self.all_context[peername] = ctx

		await ctx.send([i for i in self._handler.keys()])

		while True:
			try:
				request = (await recv(reader))
			except ConnectionResetError:
				break
			except TypeError as e:
				if str(e) == 'cannot unpack non-iterable NoneType object':
					break
				else:
					raise e
			
			if not request:
				break
			if len(request)!=3:
				raise ValueError('The data of request should be (request, args, kwargs)')
			
			request, args, kwargs = request
			if request in self._handler:
				response =  await self._handler[request](*args, **kwargs)
				await ctx.send(response)
			elif request in self._transaction:
				await self._transaction[request](ctx)

			try:
				await writer.drain()
			except ConnectionAbortedError:
				break
		del self.all_context[peername]
		writer.close()

class AoiServer_an:
	class ctx:
		EOF = b'\x00'
		def __init__(self, writer, reader, peername):
			self.writer = writer
			self.reader = reader
			self.name = peername
		
		async def send(self, data):
			await send(self.writer, data)
		
		async def send_EOF(self):
			await self.send(b'\x00')
		
		async def recv(self):
			return await recv(self.reader)

	def __init__(self, unix=False, **setting):
		self.loop = asyncio.get_event_loop()
		self.all_context = {}

		if unix:
			if 'path' not in setting:
				raise ValueError('path must be setted in unix mode')
			self.loop.create_task(asyncio.start_unix_server(self._handle_client, setting['path']))
		else:
			if 'ip' not in setting or 'port' not in setting:
				raise ValueError('ip/port must be setted in tcp mode')
			self.loop.create_task(asyncio.start_server(self._handle_client, setting['ip'], setting['port']))
	
	def run(self):
		print('Server Start')
		self.loop.run_forever()

	async def _handle_client(self,reader,writer):
		peername = await recv(reader)
		print(f'{peername} is connected')

		ctx = self.ctx(writer, reader, peername)
		self.all_context[peername] = ctx

		while True:
			try:
				data = (await recv(reader))
				if data is None:
					if writer.is_closing():
						break
					else:
						continue
			except ConnectionResetError:
				break
			except TypeError as e:
				if str(e) == 'cannot unpack non-iterable NoneType object':
					break
				else:
					raise e

			for name, other in self.all_context.items():
				if name!=ctx.name:
					await other.send([ctx.name, data])
			
			try:
				await writer.drain()
			except ConnectionAbortedError:
				break
			except ConnectionResetError:
				break
		del self.all_context[peername]
		writer.close()

if __name__=='__main__':
	server = AoiServer('127.0.0.1',12345)

	@server.request_handler
	async def test(ctx, *args, **kwargs):
		print(args, kwargs)
		return None
	
	server.run()
