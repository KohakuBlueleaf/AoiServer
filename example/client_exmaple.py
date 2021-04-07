from aoiserver.client import AoiClient
client = AoiClient(ip='127.0.0.1',port=32768)

@client.event
def message_in(data):
  _, data = data
  name, mes = data
  print(f"{name}: {mes}")

@client.transaction
def message_transfer(ctx, message):
  ctx.send(message)

client.connect()
suc = False
while not suc:
  user_name = input('請輸入用戶名稱: ')
  group = input('請輸入群組號碼: ')
  suc, state = client.login(user_name=user_name, group=group)
  print(state)

while True:
  try:
    client.message_transfer(input())
  except KeyboardInterrupt:
    break
client.close()
