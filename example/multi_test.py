from multiprocessing import Pool,freeze_support
from time import sleep
from aoiserver.client import AoiClient_an
from aoiserver.server import AoiServer_an


def multi_process_client(id):
	try:
		client = AoiClient_an(ip='127.0.0.1',port=32768)

		@client.set_handler
		def message_in(data):
			name, recv_data = data
			print(f'{name}: {recv_data}')
		sleep(0.1)

		client.send(id); sleep(0.1)
		client.close()
	except KeyboardInterrupt:
		pass

def multi_process_server():
	try:
		server = AoiServer_an(ip='127.0.0.1',port=32768)
		server.run()
	except KeyboardInterrupt:
		pass


if __name__=='__main__':
	pool = Pool(5)
	x=pool.apply_async(multi_process_server)
	y=pool.map_async(multi_process_client,range(4))
	
	try:
		x.get()
		y.get()
	except KeyboardInterrupt:
		pass

	pool.close()
	pool.join()