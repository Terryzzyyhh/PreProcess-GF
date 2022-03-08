#!/usr/bin/python 3.8
# Author:Yuhang Zhang
# @Time:2021/12/8 14:49
from osgeo import gdal
from osgeo_utils import gdal_pansharpen

# def PanSharpen(mss, pan, ofn):
#   ds = gdal.Open(mss, GA_ReadOnly)
#   nb = ds.RasterCount
#   ds = None
#   vrt = """<VRTDataset subClass="VRTPansharpenedDataset">
#   <PansharpeningOptions>
#     <PanchroBand>
#       <SourceFilename relativeToVRT="0">%s</SourceFilename>
#       <SourceBand>1</SourceBand>
#     </PanchroBand>\n""" % pan
#   for i in range(nb):
#     vrt += """    <SpectralBand dstBand="%s">
#       <SourceFilename relativeToVRT="0">%s</SourceFilename>
#       <SourceBand>%s</SourceBand>
#     </SpectralBand>\n""" % (i+1, mss, i+1)
#   vrt += """  </PansharpeningOptions>
# </VRTDataset>\n"""
#   pansharpends = gdal.Open(vrt)
#   newds = gdal.GetDriverByName('GTiff').CreateCopy(ofn, pansharpends)cls
#   pansharpends = newds = None

def PanSharpen2(mss,pan,outfiel):
  gdal_pansharpen.gdal_pansharpen(['', '-b', '1', '-b', '2', '-b', '3', '-b','4',
                                   '-of','GTiff','-threads','6','-bitdepth','16,',
                                   '-nodata' ,'0',
                                   pan, mss, outfiel])

if __name__ == '__main__':
    mss=r"G:\Hilmand_Sen2_3mth\GF6\2.两期数据预处理\GF6_PMS_E64.2_N31.3_20210224_L1A1120083674-MUX_rpcortho.dat"
    pan=r"G:\Hilmand_Sen2_3mth\GF6\2.两期数据预处理\GF6_PMS_E64.2_N31.3_20210224_L1A1120083674-PAN_rpcortho.dat"
    ofn=r"G:\GF6_PMS_E64.2_N31.3_20210224_L1A1120083674_sharpen.tif"
    PanSharpen2(mss, pan, ofn)