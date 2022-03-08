import glob
import os
import sys
import tarfile  # 解压缩
import json
import numpy as np
from osgeo import gdal
import pdb
import math
import time
import xml.dom.minidom  # 读取xml格式的影像头文件
from tqdm import tqdm  # 进度条
from Py6S import *
import argparse
from BaseTool import MeanDEM
import shutil
import torch


def RadACBlock(orthtif,tifxml,outtif,SatelliteID, SensorID, Year, config):

    IDataSet=gdal.Open(orthtif)
    # 设置输出波段
    Driver = IDataSet.GetDriver()
    geoTransform1 = IDataSet.GetGeoTransform()
    proj1 = IDataSet.GetProjection()
    cols = IDataSet.RasterXSize
    rows = IDataSet.RasterYSize
    bandcout=IDataSet.RasterCount
    ImageType=os.path.basename(orthtif).split("-")[1][:3]
    if ImageType in ("MSS MUX WFV") :
        print("------多光谱波段大气校正-------")
        OutRCname = outtif
        outDataset = Driver.Create(OutRCname, cols, rows,bandcout, gdal.GDT_Int16)
        outDataset.SetGeoTransform(geoTransform1)
        outDataset.SetProjection(proj1)
        # 分别读取4个波段
        for m in range(1, bandcout+1):
            ReadBand = IDataSet.GetRasterBand(m)
            outband = outDataset.GetRasterBand(m)
            outband.SetNoDataValue(0)
            # 获取对应波段的增益gain和偏移bias
            if ImageType=="MUX":
                ImageType="MSS"
            Gain, Bias = RadiometricCalibration(m,SatelliteID, SensorID, Year,ImageType,config)

            # 获取大气校正系数
            AtcCofa, AtcCofb, AtcCofc = AtmosphericCorrection(tifxml,m,SatelliteID, SensorID, config)
            nBlockSize = 8192
            i = 0
            j = 0
            b = cols * rows
            # 进度条参数
            XBlockcount = math.ceil(cols / nBlockSize)
            YBlockcount = math.ceil(rows / nBlockSize)
            try:
                with tqdm(total=XBlockcount * YBlockcount, iterable='iterable', desc='第%i波段:' % m) as pbar:
                    # with tqdm(total=XBlockcount*YBlockcount) as pbar:
                    # print(pbar)
                    while i < rows:
                        while j < cols:
                            # 保存分块大小
                            nXBK = nBlockSize
                            nYBK = nBlockSize

                            # 最后不够分块的区域，有多少读取多少
                            if i + nBlockSize > rows:
                                nYBK = rows - i
                            if j + nBlockSize > cols:
                                nXBK = cols - j

                            # 分块读取影像
                            Image = ReadBand.ReadAsArray(j, i, nXBK, nYBK)
                            Image = Image.astype(np.int16)
                            Image = torch.from_numpy(Image).to(device='cuda:0', dtype=torch.double)
                            outImage = torch.where(Image > 0, Image * Gain + Bias, 0.)
                            y = torch.where(outImage != 0, AtcCofa * outImage - AtcCofb, 0.)
                            atcImage = torch.where(y != 0, (y / (1 + y * AtcCofc)) * 10000, 0.)
                            atcImage = atcImage.cpu().numpy()

                            outband.WriteArray(atcImage, j, i)

                            j = j + nXBK
                            time.sleep(1)
                            pbar.update(1)
                        j = 0
                        i = i + nYBK
            except KeyboardInterrupt:
                pbar.close()
                raise
            pbar.close()
    else:
        time.sleep(3)
        print("------全色波段只辐射定标-------")
        OutRCname = outtif
        outDataset = Driver.Create(OutRCname, cols, rows, 1, gdal.GDT_Int16)
        outDataset.SetGeoTransform(geoTransform1)
        outDataset.SetProjection(proj1)
        ReadBand = IDataSet.GetRasterBand(1)
        outband = outDataset.GetRasterBand(1)
        outband.SetNoDataValue(0)
        # 获取对应波段的增益gain和偏移bias
        Gain, Bias = RadiometricCalibration(1,SatelliteID, SensorID, Year,ImageType,config)
        nBlockSize = 8192
        i = 0
        j = 0
        b = cols * rows
        # 进度条参数
        XBlockcount = math.ceil(cols / nBlockSize)
        YBlockcount = math.ceil(rows / nBlockSize)
        try:
            with tqdm(total=XBlockcount * YBlockcount, iterable='iterable', desc='%s' % os.path.basename(orthtif) )as pbar:
                # with tqdm(total=XBlockcount*YBlockcount) as pbar:
                # print(pbar)
                while i < rows:
                    while j < cols:
                        # 保存分块大小
                        nXBK = nBlockSize
                        nYBK = nBlockSize

                        # 最后不够分块的区域，有多少读取多少
                        if i + nBlockSize > rows:
                            nYBK = rows - i
                        if j + nBlockSize > cols:
                            nXBK = cols - j

                        # 分块读取影像
                        Image = ReadBand.ReadAsArray(j, i, nXBK, nYBK)
                        Image = Image.astype(np.int16)
                        Image = torch.from_numpy(Image).to(device='cuda:0', dtype=torch.double)
                        outImage = torch.where(Image > 0, Image * Gain + Bias, 0.)
                        atcImage = outImage.cpu().numpy()
                        outband.WriteArray(atcImage, j, i)
                        j = j + nXBK
                        time.sleep(1)
                        pbar.update(1)
                    j = 0
                    i = i + nYBK
        except KeyboardInterrupt:
            pbar.close()
            raise
        pbar.close()

# 辐射定标
def RadiometricCalibration(BandId,SatelliteID, SensorID, Year,ImageType,config):

    if SensorID[0:3] == "WFV":
        Gain_ = config["Parameter"][SatelliteID][SensorID][Year]["gain"][BandId - 1]
        Bias_ = config["Parameter"][SatelliteID][SensorID][Year]["offset"][BandId - 1]
    else:
        Gain_ = config["Parameter"][SatelliteID][SensorID][Year][ImageType]["gain"][BandId - 1]
        Bias_ = config["Parameter"][SatelliteID][SensorID][Year][ImageType]["offset"][BandId - 1]

    return Gain_, Bias_


# 6s大气校正
def AtmosphericCorrection(metedata,BandId,SatelliteID, SensorID, config):

    # 读取头文件
    dom = xml.dom.minidom.parse(metedata)

    # 6S模型
    s = SixS()

    # 传感器类型 自定义
    s.geometry = Geometry.User()
    s.geometry.solar_z = 90 - float(dom.getElementsByTagName('SolarZenith')[0].firstChild.data)
    s.geometry.solar_a = float(dom.getElementsByTagName('SolarAzimuth')[0].firstChild.data)
    # s.geometry.view_z = float(dom.getElementsByTagName('SatelliteZenith')[0].firstChild.data)
    # s.geometry.view_a = float(dom.getElementsByTagName('SatelliteAzimuth')[0].firstChild.data)
    s.geometry.view_z = 0
    s.geometry.view_a = 0
    # 日期
    DateTimeparm = dom.getElementsByTagName('CenterTime')[0].firstChild.data
    DateTime = DateTimeparm.split(' ')
    Date = DateTime[0].split('-')
    s.geometry.month = int(Date[1])
    s.geometry.day = int(Date[2])

    # print(s.geometry)
    # 中心经纬度
    TopLeftLat = float(dom.getElementsByTagName('TopLeftLatitude')[0].firstChild.data)
    TopLeftLon = float(dom.getElementsByTagName('TopLeftLongitude')[0].firstChild.data)
    TopRightLat = float(dom.getElementsByTagName('TopRightLatitude')[0].firstChild.data)
    TopRightLon = float(dom.getElementsByTagName('TopRightLongitude')[0].firstChild.data)
    BottomRightLat = float(dom.getElementsByTagName('BottomRightLatitude')[0].firstChild.data)
    BottomRightLon = float(dom.getElementsByTagName('BottomRightLongitude')[0].firstChild.data)
    BottomLeftLat = float(dom.getElementsByTagName('BottomLeftLatitude')[0].firstChild.data)
    BottomLeftLon = float(dom.getElementsByTagName('BottomLeftLongitude')[0].firstChild.data)

    ImageCenterLat = (TopLeftLat + TopRightLat + BottomRightLat + BottomLeftLat) / 4

    # 大气模式类型
    if ImageCenterLat > -15 and ImageCenterLat < 15:
        s.atmos_profile = AtmosProfile.PredefinedType(AtmosProfile.Tropical)

    if ImageCenterLat > 15 and ImageCenterLat < 45:
        if s.geometry.month > 4 and s.geometry.month < 9:
            s.atmos_profile = AtmosProfile.PredefinedType(AtmosProfile.MidlatitudeSummer)
        else:
            s.atmos_profile = AtmosProfile.PredefinedType(AtmosProfile.MidlatitudeWinter)

    if ImageCenterLat > 45 and ImageCenterLat < 60:
        if s.geometry.month > 4 and s.geometry.month < 9:
            s.atmos_profile = AtmosProfile.PredefinedType(AtmosProfile.SubarcticSummer)
        else:
            s.atmos_profile = AtmosProfile.PredefinedType(AtmosProfile.SubarcticWinter)

    # 气溶胶类型大陆
    s.aero_profile = AtmosProfile.PredefinedType(AeroProfile.Continental)

    # 下垫面类型
    s.ground_reflectance = GroundReflectance.HomogeneousLambertian(0.36)

    # 550nm气溶胶光学厚度,对应能见度为40km
    s.aot550 = 0.14497

    # 通过研究去区的范围去求DEM高度。
    pointUL = dict()
    pointDR = dict()
    pointUL["lat"] = max(TopLeftLat, TopRightLat, BottomRightLat, BottomLeftLat)
    pointUL["lon"] = min(TopLeftLon, TopRightLon, BottomRightLon, BottomLeftLon)
    pointDR["lat"] = min(TopLeftLat, TopRightLat, BottomRightLat, BottomLeftLat)
    pointDR["lon"] = max(TopLeftLon, TopRightLon, BottomRightLon, BottomLeftLon)
    meanDEM = (MeanDEM(pointUL, pointDR)) * 0.001

    # 研究区海拔、卫星传感器轨道高度
    s.altitudes = Altitudes()
    s.altitudes.set_target_custom_altitude(meanDEM)
    s.altitudes.set_sensor_satellite_level()

    # 校正波段（根据波段名称）
    if BandId == 1:
        SRFband = config["Parameter"][SatelliteID][SensorID]["SRF"]["1"]
        s.wavelength = Wavelength(0.450, 0.520, SRFband)

    elif BandId == 2:
        SRFband = config["Parameter"][SatelliteID][SensorID]["SRF"]["2"]

        s.wavelength = Wavelength(0.520, 0.590, SRFband)

    elif BandId == 3:
        SRFband = config["Parameter"][SatelliteID][SensorID]["SRF"]["3"]

        s.wavelength = Wavelength(0.630, 0.690, SRFband)

    elif BandId == 4:
        SRFband = config["Parameter"][SatelliteID][SensorID]["SRF"]["4"]
        s.wavelength = Wavelength(0.770, 0.890, SRFband)

    s.atmos_corr = AtmosCorr.AtmosCorrLambertianFromReflectance(-0.1)

    # 运行6s大气模型
    s.run()
    xa = s.outputs.coef_xa
    xb = s.outputs.coef_xb
    xc = s.outputs.coef_xc
    # x = s.outputs.values
    return (xa, xb, xc)


# if __name__ == '__main__':
#
#     '''
#         inputdir:压缩文件路径
#         LR：多光谱波段分辨率
#         HR：全色波段分辨率
#     '''
#     inputdir = r"G:\GF"
#     InputFilePath = inputdir
#     OutputFilePath =makedir(os.path.join(inputdir, "process"))
#
#     script_path = os.path.split(os.path.realpath(__file__))[0]
#     # 读取辐射校正和大气校正所需参数:增益、偏移和光谱响应函数
#     config_file = os.path.join(script_path, "RadiometricCorrectionParameter.json")
#     config = json.load(open(config_file))
#
#     tarFiles = glob.glob(os.path.join(inputdir,"*tar.gz"))
#
#     for tarFile in tarFiles:
#         print(tarFile)
#         filename = os.path.basename(tarFile)
#         fileType = filename[0:2]
#         filename_split = filename.split("_")
#
#             # GFType = filename[4:7]
#         GFType = filename_split[1][:3]
#         intputname = tarFile
#         outFileName = filename[:-7]
#         outname = os.path.join(inputdir,outFileName)
#         atcfiles = makedir(os.path.join(OutputFilePath,outFileName))
#
#
#         if GFType == 'WFV':
#             # tiffFile = glob.glob(outname + "/*.tiff")[0]
#             # metedata = glob.glob(outname+"/*.xml")[0]
#             tiffFile = glob.glob(os.path.join(outname, "*_rpcortho.dat"))
#             metedata = glob.glob(os.path.join(outname, "*.xml"))
#
#         elif GFType == 'PMS':
#             # tiffFile = glob.glob(OutputFilePath + "/*mss*.tiff")[0]
#             # metedata = glob.glob(OutputFilePath+"/*mss*.xml")[0]
#             tiffFiles = glob.glob(os.path.join(outname, "*_rpcortho.dat"))
#             metedatas = glob.glob(os.path.join(outname, "*.xml"))
#
#             for tiffFile,metedata in zip(tiffFiles,metedatas):
#                 try:
#                     IDataSet = gdal.Open(tiffFile)
#                 except Exception as e:
#                     print("文件%s打开失败" % tiffFile)
#
#                 cols = IDataSet.RasterXSize
#                 rows = IDataSet.RasterYSize
#
#                 SatelliteID = filename_split[0]
#                 SensorID = filename_split[1]
#                 Year = filename_split[4][:4]
#                 if int(Year) > 2020:
#                     Year = "2020"
#                 # re.search(r"-(\w{3}).*?_ortho", tiffFile).group(1)
#                 ImageType = os.path.basename(tiffFile).split("-")[1][0:3]
#                 RadACBlock(IDataSet)



