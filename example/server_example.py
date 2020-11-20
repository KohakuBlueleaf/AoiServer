from aoiserver.server import AoiServer,AoiServer_an

'''
##Example for Normal server
server = AoiServer(ip='127.0.0.1',port=32768)

@server.request_handler
def test():
	return "Hello Aoi Server"

server.run()
'''

##Example for Announcement Server
server = AoiServer_an(ip='127.0.0.1',port=32768)
server.run()