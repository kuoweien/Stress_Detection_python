#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 24 10:43:07 2022

@author: weien

Resource: https://www.sciencedirect.com/science/article/pii/S1746809411000292
"""

import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import def_passFilter as bandfilter
import def_Shannon as shannon
from scipy.ndimage import gaussian_filter
from scipy.signal import hilbert, chirp
from scipy import signal
from scipy.interpolate import interp1d
import seaborn as sns

#Note 2022.4.15 from草哥
#10-20HZ（人的）, rat的到30, 強化QRS後再取shannon
#bandpass後做median(基線飄移) 
#抓rpeak時用重新bandpass(4-35HZ)來抓 用T波比較小的範圍(4HZ以上 (T波是慢波))來做decision rule 避免用

#Poincaré

#%%參數調整
#開啟檔案
fs = 250
magnification = 500 #LTA3放大倍率
# url = '/Users/weien/Desktop/人體壓力測試/220413小魚Stroop Test/yu_strooptest_stroop.csv'
url = '/Users/weien/Desktop/ECG穿戴/HRV實驗/收案RawData/人體壓力測試/220510郭葦珊/'
# url = '/Users/weien/Desktop/人體壓力測試/220426陳云/Stroop+Radio.csv'
# url = '/Users/weien/Desktop/狗狗穿戴/HRV實驗/Dataset/220421Jessica/Petted.csv'
# situation = 'Stroop+Radio'
# situation = 'ECG'
situation = 'Stroop'
url_file = url+situation+'.csv'

length_s = 30
index = 1

clip_start = index*(length_s*fs) #scared 2500 #petted 10000
clip_end = (index+1)*(length_s*fs)  #scared 5000 #petted 12500


#抓rpeak相關參數
highpass_fq = 10
lowpass_fq = 20
highpass_forrpeak_fq = 5 #抓Rpeak時重新通過高通
lowpass_forrpeak_fq = 38 #抓Rpeak時重新通過低通
median_filter_length = 61
gaussian_filter_sigma =  0.03*fs #20
moving_average_ms = 2.5 
final_shift = 0 #Hibert轉換找到交零點後需位移回來 0.1*fs (int(0.05*fs))
detectR_maxvalue_range = (0.3*fs)*2  #草哥使用(0.3*fs)*2
detectR_minvalue_range = (0.5*fs)*2 
rpeak_close_range = 0.15*fs #0.1*fs

qrs_range = 80 #計算EMG時，在detect rpeak向左刪除之距離 （狗使用25 人使用30）
tpeak_range = 0 #計算EMG時，在detect rpeak向右刪除之距離 （狗使用37 人使用0）

#畫圖調的參數
# hist_binvalue = [400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400] #for dog
hist_binvalue = [400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900] #for dog


#%%取ECG Rpeak
#主程式
df=pd.read_csv(url_file).iloc[clip_start:clip_end]
rawdata = df[situation].reset_index(drop = True)
rawdata_mV = ((rawdata*(1.8/65535)-0.9)/magnification)*1000  #轉換為電壓
lowpass_data = bandfilter.lowPassFilter(lowpass_fq, rawdata_mV)  #低通
bandfilter_data = bandfilter.highPassFilter(highpass_fq, lowpass_data)    #高通
lowpass_forrpeak_data = bandfilter.lowPassFilter(lowpass_forrpeak_fq, rawdata_mV) #重新抓低通 （為了rpeak決策）
rawdata_bandfilter = bandfilter.highPassFilter(highpass_forrpeak_fq, lowpass_forrpeak_data)   #重新抓低通 （為了rpeak決策）
# median_filter_data = shannon.medfilt(bandfilter_data, median_filter_length)
dy_data = shannon.defivative(bandfilter_data) #一程微分
normalize_data = dy_data/np.max(dy_data) #正規化
see_data = (-1)*(normalize_data**2)*np.log((normalize_data**2)) #Shannon envelop
lmin_index, lmax_index = shannon.hl_envelopes_idx(see_data) #取上包絡線
lmax_data = see_data[lmax_index]
interpolate_data = shannon.interpolate(lmax_data,len(rawdata))
gaussian_data = gaussian_filter(interpolate_data, sigma=gaussian_filter_sigma)
hibert_data = np.imag(hilbert(gaussian_data))  #Hilbert取複數
movingaverage_data = shannon.movingaverage(hibert_data, moving_average_ms) #moving average
hibertmoving_data = hibert_data-movingaverage_data
zero_index = shannon.findZeroCross(hibertmoving_data)  #Positive zero crossing point
zero_shift_index = shannon.shiftArray(zero_index, final_shift) #位移結果

#Decision Rule: input分為三種 1.以RawECG找最大值 2.bandfilterECG找最大值 3.RawECG找最小值
detect_Rpeak_index, _   = shannon.ecgfindthemaxvalue(rawdata, zero_shift_index, detectR_maxvalue_range)  # RawECG抓R peak 找範圍內的最大值 
re_detect_Rpeak_index = shannon.deleteCloseRpeak(detect_Rpeak_index, rpeak_close_range) #刪除rpeak間隔小於rpeak_close_range之值

ecgbandfilter_detect_Rpeak_index, _   = shannon.ecgfindthemaxvalue(pd.Series(rawdata_bandfilter), zero_shift_index, detectR_maxvalue_range)  # bandfilterECG抓Rpeak 找範圍內的最大值 
re_ecgbandfilter_detect_Rpeak_index = shannon.deleteCloseRpeak(ecgbandfilter_detect_Rpeak_index, rpeak_close_range) #刪除rpeak間隔小於rpeak_close_range之值

detect_minRpeak_index, _   = shannon.ecgfindtheminvalue(rawdata, zero_shift_index, detectR_minvalue_range)  # ECG 抓Rpeak 找範圍內的最小值
re_detect_minRpeak_index = shannon.deleteCloseRpeak(detect_minRpeak_index, rpeak_close_range) #刪除rpeak間隔小於rpeak_close_range之值

ecgbandfilter_minRpeak_index, _   = shannon.ecgfindtheminvalue(pd.Series(rawdata_bandfilter), zero_shift_index, detectR_minvalue_range)  # ECG 抓Rpeak 找範圍內的最小值
re_ecgbandfilter_minRpeak_index = shannon.deleteCloseRpeak(ecgbandfilter_minRpeak_index, rpeak_close_range) #刪除rpeak間隔小於rpeak_close_range之值


#以下計算時所使用之參數
redetect_Rpeak_index =[]
redetect_Rpeak_index = re_ecgbandfilter_detect_Rpeak_index

time = np.linspace(0, (clip_end-clip_start)/fs, clip_end-clip_start)

#ECG相關參數計算
rrinterval = np.diff(redetect_Rpeak_index)
rrinterval = rrinterval*1000/fs    #轉為毫秒
mean_rrinterval = np.mean(rrinterval)
sd_rrinterval = np.std(rrinterval)
[niu, sigma, skew, kurt] = shannon.calc_stat(rrinterval) #峰值與偏度
rmssd_rrinterval = math.sqrt(np.mean((np.diff(rrinterval)**2))) #RMSSD
nn50_rrinterval = len(np.where(np.abs(np.diff(rrinterval))>50)[0]) #NN50 心跳間距超過50ms的個數，藉此評估交感
pnn50_rrinterval = nn50_rrinterval/len(rrinterval)


#內差rrinterval (之前為7HZ)
data_length = clip_end-clip_start
x_time = np.linspace(0, data_length, len(rrinterval))
f1 = interp1d(x_time, rrinterval) 
rrx_interpolate = np.linspace(0, data_length, data_length)
rry_interpolate = f1(rrx_interpolate)


temp_data = bandfilter.lowPassFilter(30, rawdata_mV)  #低通
signal = bandfilter.highPassFilter(5, temp_data)    #高通
# signal = normalize_data
noise = (rawdata_mV - signal)

plt.figure(figsize=(12,8))
plt.subplot(2,1,1)
plt.plot(signal, color='black')

plt.subplot(2,1,2)
plt.plot(noise, color='black')

plt.title('Measure Noise')



print('ECG RR interval')
print('Mean: {}'.format(round(mean_rrinterval),2))
print('SD: {}'.format(round(sd_rrinterval),2)) 
print('RMSSD: {}'.format(round(rmssd_rrinterval),2))
print('NN50: '+ str(nn50_rrinterval))
print('pNN50:{}'.format(round(pnn50_rrinterval),2))

print('Skew: {}'.format(round(skew,2)))
print('Kurt: {}'.format(round(kurt,2)))
print('------------------')


#%%畫圖 Shannon Algo過程

plt.figure(figsize=(12,8))
length = 8  #8張子圖

plt.subplot(length,1,1) #原始ECG
plt.plot(rawdata_mV, c='black')
plt.scatter(detect_Rpeak_index,rawdata_mV[detect_Rpeak_index],alpha=0.5)
plt.title('Original ECG Signal')

plt.subplot(length,1,2)
plt.plot(bandfilter_data, c='black')   #Output from Bandfilter
plt.title('Bandpass filter ({}-{}HZ)'.format(highpass_fq, lowpass_fq))

plt.subplot(length,1,3)
plt.plot(normalize_data, c='black')
plt.title('Normalized ECG')

plt.subplot(length,1,4)
plt.plot(see_data, c='black')
plt.title('Shannon Energy Envelop')

plt.subplot(length,1,5)
plt.plot(lmax_index, lmax_data, c='black')
plt.title('Upper envelope Curve')

plt.subplot(length,1,6)
plt.plot(gaussian_data, c='black')
# plt.title('Shannon Energy Envelop')
plt.title('Gaussian Smoothing')

plt.subplot(length,1,7)
plt.plot(hibertmoving_data, c='black')
plt.title('Hilbert Transformation') 

plt.subplot(length,1,8)
plt.plot(hibertmoving_data, c='black')
plt.scatter(zero_index,hibertmoving_data[zero_index],alpha=0.5)
plt.axhline(y=0, color='grey', linestyle='-')
plt.title('Zero Crossing') 

plt.tight_layout()


#印raw data 包括抓0 位移 跟取最小值

fig, ax = plt.subplots(6, 1, sharex = True, figsize=(12,12))

ax1 = plt.subplot(6,1,1)
ax1.plot(rawdata_mV, c='black')
ax1.scatter(zero_index,rawdata_mV[zero_index],alpha=0.5, c='r')
plt.title('Raw ECG (zero_index)')

ax2 = plt.subplot(6,1,2, sharex = ax1)
ax2.plot(rawdata_mV, c='black')
ax2.scatter(zero_shift_index,rawdata_mV[zero_shift_index],alpha=0.5, c='r')
plt.title('Raw ECG (shift index)')

ax3 = plt.subplot(6,1,3, sharex = ax1)
ax3.plot(rawdata_mV, c='black')
ax3.scatter(detect_minRpeak_index,rawdata_mV[detect_minRpeak_index],alpha=0.5, c='r')
plt.title('Raw ECG (find the min)')

ax4 = plt.subplot(6,1,4, sharex = ax1)
ax4.plot(rawdata_mV, c='black')
ax4.scatter(re_detect_minRpeak_index,rawdata_mV[re_detect_minRpeak_index],alpha=0.5, c='r')
plt.title('Raw ECG (Rpeak delete too close)')

ax5 = plt.subplot(6,1,5, sharex=ax1)
ax5.plot(rawdata_bandfilter, c='black')
ax5.scatter(re_ecgbandfilter_minRpeak_index,rawdata_bandfilter[re_ecgbandfilter_minRpeak_index],alpha=0.5, c='r')
plt.title('ECG ({}-{}HZ)'.format(highpass_forrpeak_fq, lowpass_forrpeak_fq))

ax6 = plt.subplot(6,1,6, sharex = ax1)
ax6.plot(rawdata_mV, c='black')
ax6.scatter(re_ecgbandfilter_detect_Rpeak_index,rawdata_mV[re_ecgbandfilter_detect_Rpeak_index],alpha=0.5, c='r')
plt.title('ECG ({}-{}HZ) (Rpeak delete too close)'.format(highpass_forrpeak_fq, lowpass_forrpeak_fq))

plt.tight_layout()

#%%畫圖 
#RR直方圖

sns.set_style("white")
plt.figure(figsize=(10,7), dpi= 80)
sns.histplot(rrinterval, alpha=0.6, linewidth=2, color='grey', kde=True, bins = hist_binvalue, label='RR Interval') #kde畫常態線
plt.title('{}: {}-{} (s)'.format(situation, int(clip_start/fs), int(clip_end/fs)))
plt.ylim(0,10)
plt.xlim(400,1200)
plt.grid(True)
plt.legend()


#%% 畫EMG圖
fig, ax = plt.subplots(3, 1, sharex=True, figsize=(12,6))

ax1 = plt.subplot(2,1,1) #RRinterval
ax1.plot(time,rawdata_mV,'black')
ax1.scatter(np.array(redetect_Rpeak_index)/250, rawdata_mV[redetect_Rpeak_index], alpha=0.5, c='r')
plt.ylabel('ECG (mV)')
plt.ylim(-1,1.5)

#取EMG
emg_mV  = shannon.fillRTpeakwithLinear(rawdata_mV,redetect_Rpeak_index, qrs_range, tpeak_range) #刪除rtpeak並補線性點
emg_mV_linearwithzero, emg_list = shannon.deleteRTpeak(rawdata_mV,redetect_Rpeak_index, qrs_range, tpeak_range) #刪除rtpeak並補0
emg_mV_withoutZero = shannon.deleteZero(emg_mV_linearwithzero) #

#emg轉成mV 並取rms
emg_rms = round(np.sqrt(np.mean(emg_mV_withoutZero**2)),2)

print('EMG')
print('RMS: {}'.format(emg_rms))

# ax2 = plt.subplot(3,1,2, sharex = ax1)
# ax2.plot(time,rry_interpolate,'black')
# plt.ylabel('RR(ms)')
# plt.title('RRinterval')

ax2 = plt.subplot(2,1,2, sharex = ax1)
for i in range(len(emg_list)):
    ax2.plot((emg_list[i].index)/250, emg_list[i], c='black')
plt.ylabel('EMG (mV)')
plt.title('EMG')
plt.xlabel('Time (s)')
plt.ylim(-1,1.5)

plt.tight_layout()



