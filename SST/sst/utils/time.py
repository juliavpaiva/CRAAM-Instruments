def iso_time(hustime):
    hours = hustime // 36000000
    minutes = (hustime % 36000000) // 600000
    secs = (hustime - (hours * 36000000 + minutes * 600000)) // 10000.0
    return '{0:=02d}'.format(hours)+':'+ '{0:=02d}'.format(minutes) +':'+'{0:=06.3f}'.format(secs)
