import re
with open("Conversation/conversation-6226239719.txt") as f:
    data = f.read()

pattern = re.compile(r"(```.*?```)", re.DOTALL)
data = pattern.split(data)
datam = data[0]
print(data.index(datam))
print(datam)