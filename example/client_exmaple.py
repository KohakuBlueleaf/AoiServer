from aoiserver.client import AoiClient,AoiClient_an

'''
##Example for Normal server
client = AoiClient(ip='127.0.0.1',port=32767)
print(client.test())
'''

##Example for Announcement Server
client = AoiClient_an(ip='127.0.0.1',port=32768)

@client.set_handler
def message_in(data):
	name, recv_data = data
	print(f'{name}: {recv_data}')

while True:
	try:
		data = input()
		print(f'self: {data}')
		client.send(data)
	except KeyboardInterrupt:
		break
client.close()