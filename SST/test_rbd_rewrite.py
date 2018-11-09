from sst import orbd

rbd = orbd.open("TestData/rs1150621.1700")
rbd2 = orbd.open("TestData/rs1150621.1800")
rbd3 = rbd + rbd2
rbd4 = orbd.concatenate((rbd, rbd2, rbd3))
#(rbd2 + rbd).to_fits()
#rbd.reduced().to_fits()
#rbd.to_fits()

# print(rbd.date)
# print(rbd.time)
# print(rbd.filename)
# print(rbd.type)
