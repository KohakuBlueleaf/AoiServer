from aoiserver.server import AoiServer
from aoidb.database import AoiDB

server = AoiServer(ip='127.0.0.1',port=32768)

ctx_db = AoiDB('ctx')
ctx_db.add_col('ctx',AoiServer.ctx())
ctx_db.add_col('address',str())
ctx_db.add_col('user_name',str())
ctx_db.add_col('now_group',int())

@server.event
async def on_disconnect(ctx):
	ctx_data = ctx_db.get(address=ctx.name)[0]
	ctx_db.delete(ctx_data)

@server.request_handler
def login(ctx, user_name, group):
	try:
		if ctx_db.get(user_name=user_name):
			return False, '用戶名稱重複'
		ctx_db.add_data(ctx=ctx, address=ctx.name, user_name=user_name, now_group=group)
	except:
		return False, '伺服器錯誤'
	return True, f'成功登入 名稱:{user_name}'

@server.transaction
async def message_transfer(ctx):
	self_data = ctx_db.get(address=ctx.name)[0]
	message = await ctx.recv()
	
	all_ctx = [i['ctx'] for i in ctx_db.get(now_group=self_data['now_group'])]
	await ctx.send_all([self_data['user_name'],message], all_ctx)

try:
	server.run()
except KeyboardInterrupt:
	pass