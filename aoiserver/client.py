import os,sys
import socket
from ._client_functions import *
from queue import Queue
from time import sleep,time
from threading import Thread as Th
from .object import *
import asyncio

class AoiClient_re:
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


class AoiClient:
  '''
  基於socket的客戶端框架
  支援request型 一傳一收
  transaction型 傳接自訂
  announcement型 廣播
  '''
  class ctx:
    '''
    連接物件
    主要用途為整合收發函數
    '''
    def __init__(self, client):
      self.client = client
    
    def send(self, data):
      send_with_len(self.client, data)
    
    def recv(self):
      return recv_msg(self.client)


  def __init__(self, ip, port):
    #初始化客戶端
    self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self._connect_method = lambda:self.client.connect((ip, port))
    
    self._request_queue = {}
    self._transaction_queue = {}
    self._event = {}


  '''功能函數'''
  def connect(self):
    #連線
    self._connect_method()
    
    #建立ctx物件
    self.ctx = AoiClient.ctx(self.client)

    #從伺服器獲取所有request method的名稱
    all_request_method = self.ctx.recv()
    for method in all_request_method:
      def func(*args, **kwargs):
        '''
        request的運作模式:
        傳送method為"request"的request物件
        data參數則為[欲呼叫之method名稱, 執行id(使用time函數之值保證每次呼叫皆相異), args, kwargs]
        get_response_for_request即是使用method名稱及rid來獲取資料
        '''
        rid = time()
        self.ctx.send(request('request',[method,rid,args,kwargs]))
        return self._get_response_for_request(method, rid)
      
      setattr(self, method, func)
      self._request_queue[method] = {}

    #建立接收資料之線程(stoppable)
    self.handler_thread = AoiThread(target=self._handle_message)
    self.handler_thread.start()

  def send(self,data):
    '''
    傳送廣播訊息
    '''
    self.ctx.send(request('announcement',data))
  
  def close(self):
    self.client.close()
    self.handler_thread.stop()
  
  '''內部使用之功能函數'''
  def _handle_message(self):
    '''
    接收所有傳入訊息並分類
    '''
    while True:
      try:
        response = self.ctx.recv()
      except ConnectionAbortedError:
        #斷線即跳出
        break
      
      #回傳訊息的data部分
      data = response.data

      #依照對應的method做分類
      if response.method == 'announcement':
        #廣播訊息呼叫event: message_in來進行處理
        self.message_in(response.data)
      
      elif response.method == 'request':
        #request的回傳資料丟入專門的dict中
        #_get_response_for_request會持續搜索該dict直到值被投入
        rmethod, rid, state, response = data
        if state:
          self._request_queue[rmethod][rid] = response
        else:
          raise ServerError(response)
      
      elif response.method == 'transaction':
        #同request
        tmethod, tid, response = data
        self._transaction_queue[tmethod][tid].append(response)

  def _get_response_for_request(self, method, rid):
    while rid not in self._request_queue[method]:
      sleep(0.0001)
    return self._request_queue[method][rid]

  def _get_response_for_transaction(self, method, tid):
    target = self._transaction_queue[method]
    while tid not in target or target[tid]==[]:
      sleep(0.0001)
    return target[tid].pop(0)
  

  '''修飾器'''
  def event(self, func):
    '''
    設定事件函數
    (目前只有message_in)
    '''
    setattr(self, func.__name__, func)
    return func

  def transaction(self, func):
    name = func.__name__
    
    def function(*args, **kwargs):
      tid = time()
      self.ctx.send(request('transaction',[name,tid]))
      self._transaction_queue[name][tid] = []
      
      class trans_ctx:
        def __init__(self, client):
          self.client = client
        
        def send(self, data):
          send_with_len(self.client.client, data)

        def recv(self):
          return self.client._get_response_for_transaction(name, tid)
      
      return func(trans_ctx(self), *args, **kwargs)
    
    self._transaction_queue[name] = {}
    setattr(self, name, function)
    return function
    
  '''event預設空函數'''
  @staticmethod
  def message_in(data):
    pass

if __name__=='__main__':
  client = AoiClient()
  client.test()