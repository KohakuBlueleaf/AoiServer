import socket,asyncio
import os,sys
import json
from time import time,ctime
from traceback import format_exc
from ._server_functions import recv,send
from .object import *
from aoidb.database import AoiDB

class AoiServer_re:
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
				response = await self._handler[request](*args, **kwargs)
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

		while not writer.is_closing():
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



class AoiServer:
	'''
	基於socket的伺服器框架
	支援request型 一傳一收
	transaction型 傳接自訂
	announcement型 廣播
	'''
	class ctx:
		'''
		連接物件
		主要用途為整合收發函數
		'''
		def __init__(self, writer=None, reader=None, peername=''):
			self.writer = writer
			self.reader = reader
			self.name = peername
		
		async def send(self, data):
			await send(self.writer, data)
		
		async def recv(self):
			return await recv(self.reader)


	def __init__(self,ip,port):
		#事件迴圈
		self.loop = asyncio.get_event_loop()
		
		#所有的連入ctx
		self.all_ctx = {}

		#request method and transaction method
		self._request = {}
		self._transaction = {}
		
		#創建事件
		self.loop.create_task(asyncio.start_server(self._handle_client, ip, port))

	def run(self):
		'''
		開始運行
		'''
		print('Server Start')
		self.loop.run_forever()

	
	'''內部使用之功能函數'''
	def _deal_request(self, ctx, request):
		method, rid, args, kwargs = request
		return method, rid, True, self._request[method](ctx, *args, **kwargs)
	
	async def _deal_transaction(self, request, writer, reader,  peername):
		#獲取客戶端要求之transaction函數名稱及tid
		method, tid = request

		#獲取所有連接物件(用於send_all)
		all_ctx = self.all_ctx.values()

		class trans_ctx:
			'''
			為了transcation所特製化的連接物件
			主要修改為:
				send整合了response物件 自動包裝method名稱,tid
				增加send_all 可以傳送廣播訊息給指定ctx(預設全部)
			'''
			def __init__(self, writer, reader, peername):
				self.writer = writer
				self.reader = reader
				self.name = peername
			
			async def send(self, data):
				await send(self.writer, response('transaction',[method,tid,data]))
			
			async def send_all(self, data, all_ctx=all_ctx):
				for i in all_ctx:
					await i.send(response('announcement',[self.name, data]))

			async def recv(self):
				return await recv(self.reader)
		
		#運行transaction函數
		await self._transaction[method](trans_ctx(writer, reader, peername))

	async def _handle_client(self,reader,writer):
		'''
		客戶端的連接處理
		'''

		#連接後獲取peername(ip,port)
		peername = ':'.join([str(i) for i in writer.get_extra_info('peername')])
		print(f'{peername} is connected')

		#建立本次連接之連接物件
		ctx = self.ctx(writer, reader, peername)
		self.all_ctx[peername] = ctx

		#若有設定on_connect event就執行(會傳入本次連接之ctx物件)
		if hasattr(self, 'on_connect'):
			await self.on_connect(ctx)

		#傳送所有的request method給客戶端
		await ctx.send([i for i in self._request.keys()])

		#聆聽迴圈
		while not writer.is_closing():
			try:
				#獲取request
				request = (await recv(reader))
				if request is None:
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
			
			#獲取本次請求之method種類(request,transaction,announcement)
			#獲取本次請求之傳入data
			method = request.method
			data = request.data

			#針對method不同做分類處理
			if method=='announcement':
				for other_ctx in self.ctx_db:
					name = other_ctx['name']
					other = other_ctx['ctx']
					if name!=ctx.name:
						await other.send(response('announcement', [ctx.name, data]))
			
			elif method=='request':
				try:
					await ctx.send(response('request', self._deal_request(ctx, data)))
				except Exception as e:
					rmethod, rid = request.data[0:1]
					await ctx.send(response('request', [rmethod, rid, False, format_exc()]))
			
			elif method=='transaction':
				await self._deal_transaction(request.data,writer,reader,peername)
			
			try:
				await writer.drain()
			except ConnectionAbortedError:
				break
			except ConnectionResetError:
				break
		
		print(f'{peername} is disconnected')

		if hasattr(self, 'on_disconnect'):
			await self.on_disconnect(ctx)
		
		del self.all_ctx[peername]
		writer.close()


	'''修飾器'''
	def event(self, func):
		setattr(self, func.__name__, func)
		return func

	def request_handler(self, func):
		self._request[func.__name__] = func
		return func

	def transaction(self, func):
		self._transaction[func.__name__] = func
		return func


if __name__=='__main__':
	server = AoiServer('127.0.0.1',12345)

	@server.request_handler
	async def test(ctx, *args, **kwargs):
		print(args, kwargs)
		return None
	
	server.run()
