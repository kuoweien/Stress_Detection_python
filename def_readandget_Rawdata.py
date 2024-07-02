#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep  3 17:21:18 2021

@author: weien
"""

import pandas as pd
import matplotlib.pyplot as plt
import datetime
from scipy import signal
import numpy as np
import def_dataDecode as dataDecode

# 讀Raw檔
def openRawFile(filename):
    
    with open(filename,'rb') as f:
        rawtxt = f.read()
    rawlist=dataDecode.dataDecode.rawdataDecode(rawtxt)
    
    rawdata=rawlist[0]
    ecg_rawdata=rawdata[0]#取原始資料channel1 (234是加速度)
    
    frquency=rawlist[1]
    ecg_fq=frquency[0]#頻率 狗狗的是250Hz
    
    updatetime_str=rawlist[2].split(' ')[1]#抓上傳時間
    update_datetime = datetime.datetime.strptime(updatetime_str, '%H:%M:%S')#上傳時間字串轉datetime type

    return ecg_rawdata,ecg_fq,update_datetime


# 輸入時間，取出時間斷之rawdata
def inputtimetoClipRawdata(ecgrawlist, frequency, updatetime, clip_start_time, clip_end_time, ):
    
    start_datetime = datetime.datetime.strptime(clip_start_time, '%H:%M:%S')
    end_datetime = datetime.datetime.strptime(clip_end_time, '%H:%M:%S')

    start_time_index = start_datetime-updatetime
    end_time_index = end_datetime-updatetime
    
    start_index = start_time_index.total_seconds()
    end_index = end_time_index.total_seconds()
        
    rawdata_list = ecgrawlist[int(start_index*frequency):int(end_index*frequency)]
    
    return rawdata_list


# 計算補數
def get_data_complement(signal): # 2的補數 有的設備因為有存正負號
    np_signal=np.array(signal)
    for i in range(len(np_signal)):
        if np_signal[i]<32768:
            np_signal[i]+=65535
    np_signal-=65535      
    return np_signal 

'''
# 讀Rawdata並取片段
def readRawdata(url, filename, cliptime_start_str, cliptime_end_str): #不需要補數 #若不需要切時間點，則cliptime_start_str='', cliptime_end_str=''
    
    ecg_rawdata, ecg_fq, updatetime = openRawFile(url+'/'+filename) #minus_V = -0.9
    if len(cliptime_start_str) != 0 and len(cliptime_end_str) != 0:
        ecg_rawdata = getConditionRawdata(cliptime_start_str, cliptime_end_str, ecg_rawdata, ecg_fq, updatetime)
    
    return ecg_rawdata, ecg_fq, updatetime

# 讀需要補數的Data
def readComplementRawdata(url, filename, cliptime_start_str, cliptime_end_str): #需要對Rawdata做補數 (硬體的關係) #若沒有要切時間點，則cliptime_start_str='', cliptime_end_str=''
    
    ecg_rawdata, ecg_fq, updatetime = openRawFile(url+'/'+filename) #minus_V = -0.9
    if len(cliptime_start_str) != 0 and len(cliptime_end_str) != 0:
        ecg_rawdata = getConditionRawdata(cliptime_start_str, cliptime_end_str, ecg_rawdata, ecg_fq, updatetime)
    # ecg_rawdata = get_data_complement(ecg_rawdata) 
    np_signal=np.array(ecg_rawdata)
    for i in range(len(np_signal)):
        if np_signal[i]<32768:
            np_signal[i]+=65535
    np_signal-=65535  
    # ecg_rawdata = ((np.array(ecg_rawdata)*(1.8/65535)-0.0)/120)*1000  #轉換為電壓

    return np_signal, ecg_fq, updatetime
'''

def outputDatatoCSV(column_name, data, outputurl):
    df = pd.DataFrame({column_name: data})
    df.to_csv(outputurl)
    
def ecgEpochScore(ecg):
    rms = np.sqrt(np.mean(np.array(ecg)**2))
    noise_score = ((rms-753.632)/(32767-753.632))*100
    
    return noise_score

def exporttomV_lta3(ecg):
    ecg_mV = ((ecg*(1.8/65535)-0.9)/250)*1000
    return ecg_mV
    
def exporttomV_patch(ecg):
    ecg_mV = ((ecg*(1.8/65535)-0.0)/120)*1000
    return ecg_mV
    


if __name__ == '__main__':

    '''------------------------Unzip Raw File---------------------------'''

    raw_url = 'Data/Rawdata/LTA3_Rawdata/'
    filename = '49-220830a.241'
    n = 49  # Participant's number

    # Adjust the different between devices time and standard time (>0 means devices time is faster)
    adjusttime_hr = 0
    adjusttime_min = 0
    adjusttime_sec = 0

    rawfile_url = raw_url + filename  # unzip url
    ecg_raw, fs, updatetime = openRawFile(rawfile_url)  # unzip raw file
    # ecg_raw = getRawdata.get_data_complement(ecg_raw) # get complement data

    # print raw data plot
    # plt.figure(figsize=(12,6))
    # plt.plot(np.linspace(0, 200, len(ecg_mV)), ecg_mV ,'black')
    # plt.xlim(0,200)
    # plt.ylim(-1,1.5)
    # plt.ylabel('ECG (mV)', fontsize=14)
    # plt.xlabel('Time (s)', fontsize=14)
    # plt.xticks(fontsize=12)
    # plt.yticks(fontsize=12)
    # ecg_raw = ecg_raw*-1

    '''------------------------save csv file of each situation data---------------------------'''

    # read protocl time
    time_url = 'Data/BasicData/Protocal_Time.xlsx'
    df_time = pd.read_excel(time_url)
    df_onedata = df_time[df_time['N'] == n]

    # Human
    columns = ['Baseline', 'Stroop', 'Baseline_after_stroop', 'Arithmetic', 'Baseline_after_Arithmetic', 'Speech',
               'Speech_3m', 'Baseline_after_speech']
    # Dog
    # columns = ['Baseline', 'Touch', 'Baseline_after_touch', 'Scared', 'Baseline_after_Scared', 'Play', 'Baseline_after_Play', 'Seperate', 'Baseline_after_Seperate', 'Eat', 'Baseline_after_Eat']

    for i in columns:

        time = ((df_onedata[i]).tolist())[0]
        if str(time) == 'nan':
            print('This parrticipant (N{}) has no time data'.format(n))
            continue

        adjust_totalseconds = adjusttime_hr * 3600 + adjusttime_min * 60 + adjusttime_sec

        start_time = time.split('-')[0]
        start_time_datetime = datetime.datetime.strptime(start_time, '%H:%M:%S')
        start_time = (start_time_datetime + datetime.timedelta(seconds=adjust_totalseconds)).strftime('%H:%M:%S')

        end_time = time.split('-')[1]
        end_time_datetime = datetime.datetime.strptime(end_time, '%H:%M:%S')
        end_time = (end_time_datetime + datetime.timedelta(seconds=adjust_totalseconds)).strftime('%H:%M:%S')

        ecg_condition = inputtimetoClipRawdata(ecg_raw, fs, updatetime, start_time, end_time)  # 取時間

        df = pd.DataFrame({'ECG': ecg_condition})
        outputurl = 'Data/ClipSituation_CSVfile/N{}/{}.csv'.format(n, i)
        df.to_csv(outputurl)

        plt.figure(figsize=(12, 2))
        plt.plot(ecg_condition, 'black')
        plt.title(i)

    
    

    



