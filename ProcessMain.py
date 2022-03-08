#!/usr/bin/python 3.8
# Author:Yuhang Zhang
# @Time:2021/12/9 0:07
import glob
import json
import os.path
from BaseTool import *
from OrthoCor import OrthoCorInDEM
from Rad_AC_GF import RadACBlock
from Sharpen import PanSharpen2
import warnings
warnings.filterwarnings("ignore")


GFrlcfg = {
    'GF1': {'WFV': '16', 'MSS': '8', 'PAN': '2'},
    'GF1B': {'WFV': '16', 'MUX': '8', 'PAN': '2'},
    'GF1C': {'WFV': '16', 'MUX': '8', 'PAN': '2'},
    'GF1D': {'WFV': '16', 'MUX': '8', 'PAN': '2'},
    'GF2': {'MSS': '4', 'PAN': '1'},
    'GF6': {'WFV': '16', 'MSS': '8', 'PAN': '2'},
}


def Main(inputdir,  *,dem=None):
    prjdir = makedir(os.path.join(inputdir, "temprocess"))

    # 读取辐射校正和大气校正所需参数:增益、偏移和光谱响应函数
    script_path = os.path.split(os.path.realpath(__file__))[0]
    config_file = os.path.join(script_path, "RadiometricCorrectionParameter.json")
    config = json.load(open(config_file))
    tarFiles = glob.glob(os.path.join(inputdir, "*tar.gz"))
    for gftarfile in tarFiles:
        '''1.解压'''
        print(gftarfile)
        print("......解压缩......")
        Filename, SatelliteID, GFType, SensorID, Year = GetMsgFromTar(gftarfile)
        if int(Year) > 2022:
            Year = "2021"
        if int(Year)<2014:
            Year = "2014"
        untardir = makedir(os.path.join(prjdir, "untar", Filename))
        untar(gftarfile, untardir)

        '''2.正射校正'''

        if GFType == 'WFV':
            print("GFType:",GFType)
            print("正射校正+大气校正")
            mssresolution = 16
            multibandtiff = glob.glob(untardir + "/*.tiff")[0]
            metedata = glob.glob(untardir + "/*.xml")[0]
            orthdir = makedir(os.path.join(prjdir, Filename ))
            otrhtifpath = os.path.join(orthdir, multibandtiff.replace(".tiff", "_orth.tiff"))
            OrthoCorInDEM(multibandtiff, otrhtifpath, mssresolution, refdem=dem)
            radacdir = makedir(os.path.join(prjdir, Filename + "radac"))
            metedatas = glob.glob(untardir + "/*.xml")
            orthtifs = glob.glob(os.path.join(prjdir, Filename + "orth", "*.tiff"))
            for orthtif, metedata in zip(orthtifs, metedatas):
                outtif = os.path.join(radacdir, os.path.basename(orthtif).replace(".tiff", "_radac.tiff"))
                RadACBlock(orthtif, metedata, outtif, SatelliteID, SensorID, Year, config)


        elif GFType == 'PMS':
            print("GFType:", GFType)
            print("正射校正+大气校正+融合")
            if len(SatelliteID)==3:
                mssresolution = int(GFrlcfg[SatelliteID]["MSS"])
                MSStiffFile = glob.glob(untardir + "/*MSS*.tiff")[0]
            else:
                mssresolution = int(GFrlcfg[SatelliteID]["MUX"])
                MSStiffFile = glob.glob(untardir + "/*MUX*.tiff")[0]

            orthdir = makedir(os.path.join(prjdir,Filename+"orth"))
            otrhtifpath = os.path.join(orthdir, os.path.basename(MSStiffFile).replace(".tiff", "_orth.tiff"))
            OrthoCorInDEM(MSStiffFile, otrhtifpath, mssresolution, refdem=dem)

            PantiffFile =glob.glob(untardir + "/*PAN*.tiff")[0]
            panresolution = int(GFrlcfg[SatelliteID]["PAN"])
            otrhtifpath = os.path.join(orthdir, os.path.basename(PantiffFile).replace(".tiff", "_orth.tiff"))
            OrthoCorInDEM(PantiffFile, otrhtifpath, panresolution, refdem=dem)


            radacdir = makedir(os.path.join(prjdir, Filename+"radac"))
            metedatas= glob.glob(untardir+"/*.xml")
            orthtifs=glob.glob(os.path.join(prjdir, Filename+"orth","*.tiff"))
            for orthtif, metedata in zip(orthtifs, metedatas):
                outtif=os.path.join(radacdir,os.path.basename(orthtif).replace(".tiff", "_radac.tiff"))
                RadACBlock(orthtif,metedata,outtif,SatelliteID, SensorID, Year, config)


            print("Pansharpen 融合")
            sharpendir = makedir(os.path.join(prjdir,  Filename+"pansharpen"))
            radactifs = glob.glob(os.path.join(orthdir, "*.tiff"))
            outsharpentif = os.path.join(sharpendir, os.path.basename(gftarfile).replace(".tar.gz", "orth_radac_pansharp.tiff"))
            PanSharpen2(radactifs[0],radactifs[1],outsharpentif)


    #
    # shutil.rmtree(prjdir)
if __name__ == '__main__':
    Main(r"G:\兴隆湖区域影像")

