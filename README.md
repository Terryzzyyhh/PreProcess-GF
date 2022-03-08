# PreProcess-GF
The srcipt for Preprocessing GF series satellite has follow funciton:
（1）Orthophoto correction
（2）radiometric calibration 
（3）Atmospheric correction
 (4) Pansharpen

（2）、（3） can use GPU operation（but you must install pytorch）

the script is available on GF1（WFV，PMS）、GF1（BCD）,GF2(PMS),GF6(WFV、PMS)


How to use:
put *zip raw files in one file folder ,change the path of the folder at Main function in ProcessMain.py and run
