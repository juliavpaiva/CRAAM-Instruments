from sst import orbd

rbd = orbd.open("TestData/rs990909.1700")

print(rbd.date)
print(rbd.time)
print(rbd.filename)
print(rbd.type)