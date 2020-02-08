from datetime import datetime, timedelta

def time(jd):

    time = str((datetime(2001, 1, 1) + timedelta(seconds=jd)).time())
    return time

def date(jd):

    date = str((datetime(2001, 1, 1) + timedelta(seconds=jd)).date())
    return date