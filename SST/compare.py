import numpy as np

from sst import orbd_old

d1=orbd_old.RBD(PathToXML="/Users/bruno/mack/craam/CRAAM-Instruments/SST/sst/XMLtables")
d1.readRBDinDictionary('TestData/rs1150621.1700')

from sst import orbd

rbd = orbd.open("TestData/rs1150621.1700")

#d1 data is a dictionary so cant be compared directly to rbd data
#which is a numpy array.
for column in rbd.columns:
    if not np.array_equal(d1.Data[column], rbd.data[column]):
        print("Column {} is not equal!!!".format(column))
    else:
        print("Column {} OK!".format(column))