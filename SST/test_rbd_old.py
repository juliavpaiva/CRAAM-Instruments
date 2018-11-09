from sst import orbd_old

d1=orbd_old.RBD(PathToXML="/Users/bruno/mack/craam/CRAAM-Instruments/SST/sst/XMLtables")
d1.readRBDinDictionary('TestData/rs1150621.1700')
#d1.reduced()
#d1.writeFITS()

# print(d1.MetaData["ISODate"])
# print(d1.MetaData["ISOTime"])
# print(d1.MetaData["RBDFileName"])
# print(d1.MetaData["SSTType"])
