from sst import orbd_old

d1=orbd_old.RBD(PathToXML="/Users/bruno/mack/craam/CRAAM-Instruments/SST/sst/rbd/XMLtables")
d1.readRBDinDictionary('TestData/rs1150621.1700')

from sst import orbd

rbd = orbd.open("TestData/rs1150621.1700")

print(d1.Data["time"] == rbd.data["time"])