#!usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author  : zhaoguanhua
@Email   : zhaogh@hdsxtech.com
@Time    : 2019/12/25 14:00
@File    : BaseTool.py
@Software: PyCharm
"""

import os
import shutil
import tarfile
from osgeo import gdal
import numpy as np
import osgeo_utils




def MeanDEM(pointUL, pointDR):
    '''
    计算影像所在区域的平均高程.
    '''
    script_path = os.path.split(os.path.realpath(__file__))[0]
    dem_path = os.path.join(script_path, "GMTED2km.tif")

    try:
        DEMIDataSet = gdal.Open(dem_path)
    except Exception as e:
        pass

    DEMBand = DEMIDataSet.GetRasterBand(1)
    geotransform = DEMIDataSet.GetGeoTransform()
    # DEM分辨率
    pixelWidth = geotransform[1]
    pixelHight = geotransform[5]

    # DEM起始点：左上角，X：经度，Y：纬度
    originX = geotransform[0]
    originY = geotransform[3]

    # 研究区左上角在DEM矩阵中的位置
    yoffset1 = int((originY - pointUL['lat']) / pixelWidth)
    xoffset1 = int((pointUL['lon'] - originX) / (-pixelHight))

    # 研究区右下角在DEM矩阵中的位置
    yoffset2 = int((originY - pointDR['lat']) / pixelWidth)
    xoffset2 = int((pointDR['lon'] - originX) / (-pixelHight))

    # 研究区矩阵行列数
    xx = xoffset2 - xoffset1
    yy = yoffset2 - yoffset1
    # 读取研究区内的数据，并计算高程
    DEMRasterData = DEMBand.ReadAsArray(xoffset1, yoffset1, xx, yy)

    MeanAltitude = np.mean(DEMRasterData)
    return MeanAltitude

def GetMsgFromTar(tar):
    Filename=os.path.basename(tar).replace(".tar.gz","")
    filename_split = Filename.split("_")
    SatelliteID = filename_split[0]
    SensorID = filename_split[1]
    GFType = filename_split[1][:3]
    Year = filename_split[4][:4]

    return Filename,SatelliteID,GFType,SensorID,Year


def makedir(dirstr):
    '''

    :param dirstr:
    :return:
    '''
    if (os.path.exists(dirstr)):
        shutil.rmtree(dirstr)
    os.makedirs(dirstr)
    return os.path.join(dirstr)


# 解压缩原始文件
def untar(fname, dirs):
    # print("文件路径", fname)
    try:
        t = tarfile.open(fname)
    except Exception as e:
        print("文件%s打开失败" % fname)
    t.extractall(path=dirs)