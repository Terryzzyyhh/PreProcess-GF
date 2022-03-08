import math
import numpy as np
def Cal_SRFS(begin,stop,fwhm=2.5):  
    row=fwhm/(2*math.sqrt(2*math.log(2)))
    center=(stop+begin)/2
    SRFS=[]
    num=int((stop-begin)/2.5)
    clip=np.linspace(begin,stop,num)
    for i in clip:
        srf=math.exp(-((i-center)**2)/(2*row*row))
        SRFS.append(srf)
    return SRFS

GF2srfs=Cal_SRFS(begin=450,stop=520,fwhm=2.5)
print(GF2srfs)