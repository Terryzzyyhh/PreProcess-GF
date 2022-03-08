#!/usr/bin/python 3.8
# Author:Yuhang Zhang
# @Time:2021/12/9 0:44
import sys
from osgeo import gdal,osr
import os
import math

def OrthoCorInDEM(input, output, resolution, refdem=None):
    # path=r"E:\GF\unzip\GF2_PMS1_E108.2_N29.4_20180610_L1A0003251311"
    filename = os.path.basename(input)
    if refdem==None:
        refdem = os.path.join(sys.path[0],"GMTED2km.tif")
    print(filename)
    print("RPC_DEM:",refdem,"\nResolution:",resolution,"m")

    lon = float(filename.split('_')[2][1:])
    zone_ = int(math.ceil(lon / 6)) + 30
    zone = int("326" + str(zone_))

    inputfile = gdal.Open(input)
    dstSRS = osr.SpatialReference()
    dstSRS.ImportFromEPSG(zone)
    #gdal.WarpOptions(format="Gtiff", xRes=resolution, yRes=resolution,dstSRS=dstSRS, rpc=True, transformerOptions=refdem)
    prog_func = gdal.TermProgress_nocb
    process = gdal.Warp(output, inputfile,options=gdal.WarpOptions(format="Gtiff", xRes=resolution, yRes=resolution,
                                                                   srcNodata=0, dstNodata=0,
                        callback=prog_func,dstSRS=dstSRS, rpc=True, transformerOptions=[r'RPC_DEM=%s'%refdem]))
    del process,input,output,prog_func,dstSRS
