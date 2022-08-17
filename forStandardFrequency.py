#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug  8 12:04:12 2022

@author: weien
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 26 14:01:57 2022

@author: weien
"""

import pandas as pd
import numpy as np
import def_getRpeak_main as getRpeak
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d # 導入 scipy 中的一維插值工具 interp1d
import scipy.fft
import def_readandget_Rawdata
import def_measureSQI as measureSQI
import math

def interpolate(raw_signal,n):   #signal為原始訊號 n為要插入產生為多少長度之訊號

    x = np.linspace(0, len(raw_signal)-1, num=len(raw_signal), endpoint=True)
    f = interp1d(x, raw_signal, kind='cubic')
    xnew = np.linspace(0, len(raw_signal)-1, num=n, endpoint=True)  
    
    return f(xnew)

def window_function(window_len,window_type='hanning'):
    if window_type=='hanning':
        return np.hanning(window_len)
    elif window_type=='hamming':
        return np.hamming(window_len)

def fft_power(input_signal,sampling_rate,window_type):
    w=window_function(len(input_signal))
    window_coherent_amplification=sum(w)/len(w)
    y_f = np.fft.fft(input_signal*w)
    y_f_Real= 2.0/len(input_signal) * np.abs(y_f[:len(input_signal)//2])/window_coherent_amplification
    x_f = np.linspace(0.0, 1.0/(2.0*1/sampling_rate), len(input_signal)//2)        
    return y_f_Real,x_f

def medfilt (x, k): #基線飄移 x是訊號 k是摺照大小
    """Apply a length-k median filter to a 1D array x.
    Boundaries are extended by repeating endpoints.
    """
    assert k % 2 == 1, "Median filter length must be odd."
    assert x.ndim == 1, "Input must be one-dimensional."
    k2 = (k - 1) // 2
    y = np.zeros ((len (x), k), dtype=x.dtype)
    y[:,k2] = x
    for i in range (k2):
        j = k2 - i
        y[j:,i] = x[:-j]
        y[:j,i] = x[0]
        y[:-j,-(i+1)] = x[j:]
        y[-j:,-(i+1)] = x[-1]
    return np.median (y, axis=1)  #做完之後還要再用原始訊號減此值
'''
t = np.linspace( 0, 10, 1000, endpoint = False ) # 定義時間陣列
x = np.sin( 2 * np.pi * 0.2 * t ) 
y_f_Real, x_f = fft_power(x, 100, 'hamming')

plt.figure()
plt.subplot(211)
plt.plot(t,x)
plt.subplot(212)
plt.plot(x_f,y_f_Real)
'''

n = 37

# Read data parameters
lta3_baseline = 0.9
lta3_magnification = 250
fs = 250

# Sliding window parameters
epoch_len = 150 # seconds
rr_resample_rate = 7
slidingwidow_len = 30 #seconds
epoch = 2.5 # minutes
rri_epoch = 30 # seconds
minute_to_second = 60

# Noise threshold
checknoiseThreshold = 100

# 抓Rpeak的參數
medianfilter_size = 61
gaussian_filter_sigma =  0.03*fs #20
moving_average_ms = 2.5
final_shift = 0 #Hibert轉換找到交零點後需位移回來 0.1*fs (int(0.05*fs))
detectR_maxvalue_range = (0.32*fs)*2  #草哥使用(0.3*fs)*2 #Patch=0.4*fs*2 LTA3=0.35*fs*2
rpeak_close_range = 0.15*fs #0.1*fs
lowpass_fq = 20
highpass_fq = 10

# EMG參數
qrs_range = int(0.32*fs)    # Human: int(0.32*fs)
tpeak_range = int(0.2*fs)   # Human: int(0.2*fs)


df_HRV_fqdomain = pd.DataFrame()



    
ecg_url = '/Users/weien/Desktop/ECG穿戴/實驗二_人體壓力/DataSet/ClipSituation_eachN/N{}/'.format(n)
filename_baseline = 'Baseline.csv'
filename_stroop = 'Stroop.csv'
filename_b2 = 'Baseline_after_stroop.csv'
filename_arithmetic = 'Arithmetic.csv'
filename_b3 =  'Baseline_after_Arithmetic.csv'
filename_speech = 'Speech.csv'
filename_b4 = 'Baseline_after_speech.csv'


df_baseline1 = pd.read_csv(ecg_url+filename_baseline)
df_stroop = pd.read_csv(ecg_url+filename_stroop)
df_baseline2 = pd.read_csv(ecg_url+filename_b2)
df_arithmetic = pd.read_csv(ecg_url+filename_arithmetic)
df_baseline3= pd.read_csv(ecg_url+filename_b3)
df_speech = pd.read_csv(ecg_url+filename_speech)
df_baseline4 = pd.read_csv(ecg_url+filename_b4)


ecg_baseline1 =  np.array(df_baseline1['ECG'])
ecg_stroop = np.array(df_stroop['ECG'])
ecg_baseline2 = np.array(df_baseline2['ECG'])
ecg_arithmetic = np.array(df_arithmetic['ECG'])
ecg_baseline3 = np.array(df_baseline3['ECG'])
ecg_speech = np.array(df_speech['ECG'])
ecg_baseline4 = np.array(df_baseline4['ECG'])

# Rebuild protocal data
ecg_raw = np.concatenate((ecg_baseline1, ecg_stroop, ecg_baseline2, ecg_arithmetic, ecg_baseline3, ecg_speech, ecg_baseline4))
ecg_without_noise = measureSQI.splitEpochandisCleanSignal(ecg_raw, fs, checknoiseThreshold) #兩秒為Epoch，將雜訊的Y值改為0
ecg_mV = (((np.array(ecg_without_noise))*1.8/65535-lta3_baseline)/lta3_magnification)*1000


rri_mean_list = []
rri_sd_list = []
rri_skew_list = []
rri_kurt_list = []
rri_rmssd_list = []
rri_nn50_list = []
rri_pnn50_list = []

tp_HRV = []
hf_HRV = []
lf_HRV = []
vlf_HRV = []
nLF_HRV = []
nHF_HRV = []
lfhf_ratio_hrv = []
rpeakindex_list = []
median_ecg_list = []
mnf_list = []
mdf_list = []
#%%計算頻域


columns = ['Baseline', 'Stroop',  'Arithmetic', 'Speech']
# columns = ['Baseline']


###Time domain
    
for stress in range(len(columns)):
    situation = columns[stress]
    ecg_url = '/Users/weien/Desktop/ECG穿戴/實驗二_人體壓力/DataSet/ClipSituation_eachN/N{}/{}.csv'.format(n, situation)
    df = pd.read_csv(ecg_url)
    ecg_raw = df['ECG']
    
    for i in range(10): 
        print('TimeDomian- Participant:{} Situation:{} Epoch:{}'.format(n, columns[stress], i))
        
        ecg = ecg_raw[i*fs*rri_epoch : (i+1)*rri_epoch*fs]
        if len(ecg) < (rri_epoch*fs):
            break
        ecg_nonoise = measureSQI.splitEpochandisCleanSignal(ecg, fs, checknoiseThreshold) #兩秒為Epoch，將雜訊的Y值改為0
        
    
    #單位換算
        ecg_nonoise_mV = (((np.array(ecg_nonoise))*1.8/65535-lta3_baseline)/lta3_magnification)*1000
        ecg_mV = (((np.array(ecg))*1.8/65535-lta3_baseline)/lta3_magnification)*1000
    
    #抓Rpeak
        median_ecg, rpeakindex = getRpeak.getRpeak_shannon(ecg_nonoise_mV, fs, medianfilter_size, gaussian_filter_sigma, moving_average_ms, final_shift ,detectR_maxvalue_range,rpeak_close_range)

        
    #%%計算RRI
    # RR interval
        if len(rpeakindex)<=2: #若只抓到小於等於2點的Rpeak，會無法算HRV參數，因此將參數設為0
            rri_mean =0
            rri_sd = 0
            rri_rmssd = 0
            rri_nn50 = 0
            rri_pnn50 = 0
            rri_skew = 0
            rri_kurt = 0
            
        else: #若Rpeak有多於2個點，進行HRV參數計算
            rrinterval = np.diff(rpeakindex)
            rrinterval = rrinterval/(fs/1000) #RRI index點數要換算回ms (%fs，1000是因為要換算成毫秒)
            re_rrinterval = getRpeak.interpolate_rri(rrinterval, fs)

            #RRI 相關參數
            rri_mean = np.mean(re_rrinterval)
            rri_sd = np.std(re_rrinterval)
            
            outlier_upper = rri_mean+(3*rri_sd) 
            outlier_lower = rri_mean-(3*rri_sd)
            
            re_rrinterval = re_rrinterval[re_rrinterval<outlier_upper]
            re_rrinterval = re_rrinterval[re_rrinterval>outlier_lower]  #刪除outlier的rrinterval
            
            #因有刪除outlier，所以重新計算平均與SD
            rri_mean = np.mean(re_rrinterval)
            rri_sd = np.std(re_rrinterval)
            [niu, sigma, rri_skew, rri_kurt] = getRpeak.calc_stat(re_rrinterval) #峰值與偏度
            rri_rmssd = math.sqrt(np.mean((np.diff(re_rrinterval)**2))) #RMSSD
            rri_nn50 = len(np.where(np.abs(np.diff(re_rrinterval))>50)[0]) #NN50 心跳間距超過50ms的個數，藉此評估交感
            rri_pnn50 = rri_nn50/len(re_rrinterval)
            
            rri_mean_list.append(rri_mean)
            rri_sd_list.append(rri_sd)
            rri_skew_list.append(rri_skew)
            rri_kurt_list.append(rri_kurt)
            rri_rmssd_list.append(rri_rmssd)
            rri_nn50_list.append(rri_nn50)
            rri_pnn50_list.append(rri_pnn50)

### Frequency domain


baseline_strart_index = 0*minute_to_second*fs
stroop_start_index = 5*minute_to_second*fs
arithmetic_start_index = 15*minute_to_second*fs
speech_start_index = 25*minute_to_second*fs
columns_index = [baseline_strart_index, stroop_start_index, arithmetic_start_index, speech_start_index]


for stress in range(len(columns)): # Run for four situation

    for i in range(10): # one stress situation have 10 data
    
        print('Frequency domain - Paricipant:{} Situation: {} Epoch:{}'.format(n, columns[stress], i))
        
        ecg_url = '/Users/weien/Desktop/ECG穿戴/實驗二_人體壓力/DataSet/ClipSituation_eachN/N{}/'.format(n)
        filename_baseline = 'Baseline.csv'
        filename_stroop = 'Stroop.csv'
        filename_b2 = 'Baseline_after_stroop.csv'
        filename_arithmetic = 'Arithmetic.csv'
        filename_b3 =  'Baseline_after_Arithmetic.csv'
        filename_speech = 'Speech_3m.csv'
        filename_b4 = 'Baseline_after_speech.csv'
        
        
        df_baseline1 = pd.read_csv(ecg_url+filename_baseline)
        df_stroop = pd.read_csv(ecg_url+filename_stroop)
        df_baseline2 = pd.read_csv(ecg_url+filename_b2)
        df_arithmetic = pd.read_csv(ecg_url+filename_arithmetic)
        df_baseline3= pd.read_csv(ecg_url+filename_b3)
        df_speech = pd.read_csv(ecg_url+filename_speech)
        df_baseline4 = pd.read_csv(ecg_url+filename_b4)
        
        
        ecg_baseline1 =  np.array(df_baseline1['ECG'])
        ecg_stroop = np.array(df_stroop['ECG'])
        ecg_baseline2 = np.array(df_baseline2['ECG'])
        ecg_arithmetic = np.array(df_arithmetic['ECG'])
        ecg_baseline3 = np.array(df_baseline3['ECG'])
        ecg_speech = np.array(df_speech['ECG'])
        ecg_baseline4 = np.array(df_baseline4['ECG'])
        
        # Rebuild protocal data
        ecg_raw = np.concatenate((ecg_baseline1, ecg_stroop, ecg_baseline2, ecg_arithmetic, ecg_baseline3, ecg_speech, ecg_baseline4))
        ecg_without_noise = measureSQI.splitEpochandisCleanSignal(ecg_raw, fs, checknoiseThreshold) #兩秒為Epoch，將雜訊的Y值改為0
        ecg_mV = (((np.array(ecg_without_noise))*1.8/65535-lta3_baseline)/lta3_magnification)*1000
        


        input_ecg = ecg_mV[columns_index[stress]+(i*slidingwidow_len*fs) : int((columns_index[stress]+(2.5*minute_to_second*fs)) + (i*slidingwidow_len*fs))] 
        
    # Get R peak from ECG by using shannon algorithm
        median_ecg, rpeakindex = getRpeak.getRpeak_shannon(input_ecg, fs, medianfilter_size, gaussian_filter_sigma, moving_average_ms, final_shift ,detectR_maxvalue_range,rpeak_close_range)
    
    
        if len(rpeakindex)<=2: #若只抓到小於等於2點的Rpeak，會無法算HRV參數，因此將參數設為0
                    tp_log =0
                    hf_log = 0
                    vlf_log = 0
                    nLF = 0
                    nHF = 0
                    lfhf_ratio_log = 0
                    mnf = 0
                    mdf = 0
                   
        else: #若Rpeak有多於2個點，進行HRV參數計算
                    
           # RRI計算
            rrinterval = np.diff(rpeakindex)
            rrinterval = rrinterval/(fs/1000) #RRI index點數要換算回ms (%fs，1000是因為要換算成毫秒)
            
            re_rrinterval = getRpeak.interpolate_rri(rrinterval, fs) #對因雜訊刪除的RRI進行補點
            #RRI 相關參數
            re_rri_mean = np.mean(re_rrinterval)
            re_rri_sd = np.std(re_rrinterval)
            
            outlier_upper = re_rri_mean+(3*re_rri_sd) 
            outlier_lower = re_rri_mean-(3*re_rri_sd)
            
            re_rrinterval = re_rrinterval[re_rrinterval<outlier_upper]
            re_rrinterval = re_rrinterval[re_rrinterval>outlier_lower]  #刪除outlier的rrinterval
            

            rrinterval_resample = interpolate(re_rrinterval, rr_resample_rate*epoch_len) #補點為rr_resample_rate HZ
            x_rrinterval_resample = np.linspace(0, epoch_len, len(rrinterval_resample))
            
            rrinterval_resample_zeromean=rrinterval_resample-np.mean(rrinterval_resample)
            
            # EMG計算
            emg_mV_linearwithzero, _ = getRpeak.deleteRTpeak(median_ecg,rpeakindex, qrs_range, tpeak_range) #刪除rtpeak並補0       
               
            # FFT轉頻域
            y_f_ECG, x_f_ECG = fft_power(rrinterval_resample_zeromean, rr_resample_rate, 'hanning')
            y_f_EMG, x_f_EMG = fft_power(emg_mV_linearwithzero, fs, 'hanning')
            
                
            ## Calculate HRV frequency domain parameters
            tp_index = []
            hf_index = []
            lf_index = []
            vlf_index = []
            ulf_index = []
    
            tp_index.append(np.where( (x_f_ECG<=0.4)))  
            hf_index.append(np.where( (x_f_ECG>=0.15) & (x_f_ECG<=0.4)))  
            lf_index.append(np.where( (x_f_ECG>=0.04) & (x_f_ECG<=0.15)))  
            vlf_index.append(np.where( (x_f_ECG>=0.003) & (x_f_ECG<=0.04)))   
            ulf_index.append(np.where( (x_f_ECG<=0.003)))   
            
            
            tp_index = tp_index[0][0]
            hf_index = hf_index[0][0]
            lf_index = lf_index[0][0]
            vlf_index = vlf_index[0][0]
            ulf_index = ulf_index[0][0]
            
            
            tp = np.sum(y_f_ECG[tp_index[0]:tp_index[-1]])
            hf = np.sum(y_f_ECG[hf_index[0]:hf_index[-1]])
            lf = np.sum(y_f_ECG[lf_index[0]:lf_index[-1]])
            vlf = np.sum(y_f_ECG[vlf_index[0]:vlf_index[-1]])
            # ulf = np.log(np.sum(y_f_ECG[ulf_index[0]:ulf_index[-1]]))
            nLF = (lf/(tp-vlf))*100
            nHF = (hf/(tp-vlf))*100
            lfhf_ratio_log = np.log(lf/hf)
            
            tp_log = np.log(tp)
            hf_log = np.log(hf)
            lf_log = np.log(lf)
            vlf_log = np.log(vlf)
            
            tp_HRV.append(tp_log)
            hf_HRV.append(hf_log)
            lf_HRV.append(lf_log)
            vlf_HRV.append(vlf_log)
            nLF_HRV.append(nLF)
            nHF_HRV.append(nHF)
            lfhf_ratio_hrv.append(lfhf_ratio_log)
        
        
            ## Calculate EMG frequency domain parameters
            mnf = np.sum(y_f_EMG)/len(x_f_EMG)
            y_f_EMG_integral = np.cumsum(y_f_EMG)
            mdf_median_index = (np.where(y_f_EMG_integral>np.max(y_f_EMG_integral)/2))[0][0] # Array is bigger than (under area)/2
            mdf = y_f_EMG[mdf_median_index]
            
            mnf_list.append(mnf)
            mdf_list.append(mdf)
            
            # df_HRV_fqdomain = df_HRV_fqdomain.append({'N':n, 'Epoch':i+1, 
                                                      # 'TP':tp_log , 'HF':hf_log, 'LF':lf_log, 'VLF':vlf_log,
                                                      # 'nLF':nLF, 'nHF':nHF , 'LF/HF':lfhf_ratio_log, 
                                                      # 'MNF': mnf, 'MDF': mdf
                                                     # } ,ignore_index=True)
    

    
# Frequency Domain Epoch
plt_len =9

plt.figure(figsize=(12,9))

plt.subplot(plt_len,1,1)
plt.plot(rri_mean_list, 'black')
plt.ylabel('RRI Mean')

plt.subplot(plt_len,1,2)
plt.plot(rri_sd_list, 'black')
plt.ylabel('RRI SD')


plt.subplot(plt_len,1,3)
plt.plot(tp_HRV, 'black')
plt.ylabel('TP\n$[ln(m{s^2)}$]')


plt.subplot(plt_len,1,4)
plt.plot(hf_HRV, 'black')
plt.ylabel('HF\n$[ln(m{s^2)}$]')

plt.subplot(plt_len,1,5)
plt.plot(lf_HRV, 'black')
plt.ylabel('LF\n$[ln(m{s^2)}$]')

plt.subplot(plt_len,1,6)
plt.plot(vlf_HRV, 'black')
plt.ylabel('VLF\n$[ln(m{s^2)}$]')

plt.subplot(plt_len,1,7)
plt.plot(nLF_HRV, 'black')
plt.ylabel('LF%\n(%)')

plt.subplot(plt_len,1,8)
plt.plot(nHF_HRV, 'black')
plt.ylabel('HF%\n(%)')

plt.subplot(plt_len,1,9)
plt.plot(lfhf_ratio_hrv, 'black')
plt.ylabel('LF/HF\n[ln(ratio)]')




