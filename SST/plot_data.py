def getTimeAxis(d):

    ndata = d.data['time'].shape[0]

    ssttime = np.array(np.empty(ndata),dtype=dt.datetime)
    year  = int(d.date[0:4])
    month = int(d.date[5:7])
    day   = int(d.date[8:])
    for i in np.arange(ndata):
        ms = d.data['time'][i]
        hours =  ms // 36000000
        minutes = (ms % 36000000) // 600000
        seconds = ((ms % 36000000) % 600000) / 1.0E+04
        seconds_int  = int(seconds)
        seconds_frac = seconds - int(seconds)
        useconds     = int(seconds_frac * 1e6)
        ssttime[i] = dt.datetime(year,month,day,hours,minutes,seconds_int,useconds)
                        

    return ssttime
    

if __name__ == "__main__":

    import sys
    import numpy as np
    import matplotlib.pyplot as plt
    import datetime as dt

    from sst import orbd

    if len(sys.argv) < 3 :
        print('Usage: ' + sys.argv[0] + ' RBDfilename ch')
        sys.exit(1)

    RBDfname=sys.argv[1]
    chn=int(sys.argv[2])
    
    try:
        d = orbd.open(RBDfname)
    except Exception:
        print("An unexpected exception occurred")
        sys.exit(1)

    if d.type == 'Auxiliary' :
        fieldname='adc'
    else:
        fieldname='adcval'

    st=getTimeAxis(d)
    plt.plot(st,d.data[fieldname][:,chn])
    plt.show()