# SST
  
Python modules for working with SST data.  
* orbd - Convert Raw Binary Data to FITS.
  
# How to use

```python
from sst import orbd

rbd = orbd.open("TestData/rs1150621.1700")

#Get info
print(rbd.type) # Integration
print(rbd.date) # 2015-06-21
print(rbd.time) # 18:00
print(rbd.filename) # rs1150621.1700
print(rbd.columns) # ('time', 'adcval', 'pos_time', 'azipos', 'elepos', 'pm_daz', ...)
print(rbd.data["adcval"]) # [[23836 17558 21127 16463  9802 16893] ...]

#Concatenate data
rbd2 = orbd.open("TestData/rs1150621.1800")

rbd3 = orbd.concatenate((rbd, rbd2))
#or
rbd3 = rbd + rbd2

#Reduce data
reduced = rbd.reduced() 
#Or specify which columns to keep
reduced = rbd.reduced(["time", "adcval"])

#Write data to a FITS file
rbd.to_fits()
```

# Compatibility
Python >= 3.4