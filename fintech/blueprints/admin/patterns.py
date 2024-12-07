# mypy: ignore-errors
from flask import current_app
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt, mpld3
from fintech.blueprints.admin.rolling_window import rw_top, rw_bottom, get_data_by_symbol
from typing import List
from collections import deque
from dataclasses import dataclass


@dataclass
class HSPattern:

    # True if inverted, False if not. Inverted is "bullish" according to technical analysis dogma
    inverted: bool

    # Indices of the parts of the H&S pattern
    l_shoulder: int = -1
    r_shoulder: int = -1
    l_armpit: int = -1
    r_armpit: int = -1
    head: int = -1
   
    # Price of the parts of the H&S pattern. _p stands for price.
    l_shoulder_p: float = -1
    r_shoulder_p: float = -1
    l_armpit_p: float = -1
    r_armpit_p: float = -1
    head_p: float = -1
   
    start_i: int = -1
    break_i: int = -1
    break_p: float = -1

    neck_start: float = -1
    neck_end: float = -1

    # Attributes
    neck_slope: float = -1
    head_width: float = -1
    head_height: float = -1
    pattern_r2: float = -1

def compute_pattern_r2(data: np.array, pat: HSPattern):

    line0_slope = (pat.l_shoulder_p - pat.neck_start) / (pat.l_shoulder - pat.start_i)
    line0 = pat.neck_start + np.arange(pat.l_shoulder - pat.start_i) * line0_slope
    
    line1_slope = (pat.l_armpit_p - pat.l_shoulder_p) / (pat.l_armpit - pat.l_shoulder)
    line1 = pat.l_shoulder_p + np.arange(pat.l_armpit - pat.l_shoulder) * line1_slope
    
    line2_slope = (pat.head_p - pat.l_armpit_p) / (pat.head - pat.l_armpit)
    line2 = pat.l_armpit_p + np.arange(pat.head - pat.l_armpit) * line2_slope
    
    line3_slope = (pat.r_armpit_p - pat.head_p) / (pat.r_armpit - pat.head)
    line3 = pat.head_p + np.arange(pat.r_armpit - pat.head) * line3_slope
    
    line4_slope = (pat.r_shoulder_p - pat.r_armpit_p) / (pat.r_shoulder - pat.r_armpit)
    line4 = pat.r_armpit_p + np.arange(pat.r_shoulder - pat.r_armpit) * line4_slope
    
    line5_slope = (pat.break_p - pat.r_shoulder_p) / (pat.break_i - pat.r_shoulder)
    line5 = pat.r_shoulder_p + np.arange(pat.break_i - pat.r_shoulder) * line5_slope
    
    raw_data = data[pat.start_i:pat.break_i]
    hs_model = np.concatenate([line0, line1, line2, line3, line4, line5])
    mean = np.mean(raw_data)

    ss_res = np.sum( (raw_data - hs_model) ** 2.0 )
    ss_tot = np.sum( (raw_data - mean) ** 2.0 )

    r2 = 1.0 - ss_res / ss_tot
    return r2


def hs(extrema_indices: List[int], data: np.array, i:int, early_find: bool = False) -> HSPattern:
    ''' Returns a HSPattern if found, or None if not found ''' 
    # Unpack list
    l_shoulder = extrema_indices[0]
    l_armpit = extrema_indices[1]
    head = extrema_indices[2]
    r_armpit = extrema_indices[3]

    if i - r_armpit < 2:
        return None
    

    # Find right shoulder as max price since r_armpit
    r_shoulder = r_armpit + data[r_armpit + 1: i].argmax() + 1

    # Head must be higher than shoulders
    if data[head] <= max(data[l_shoulder], data[r_shoulder]):
        return None

    # Balance rule. Shoulders are above the others midpoint.
    # A shoulder's midpoint is the midpoint between the shoulder and armpit
    r_midpoint = 0.5 * (data[r_shoulder] + data[r_armpit])
    l_midpoint = 0.5 * (data[l_shoulder] + data[l_armpit])
    if data[l_shoulder] < r_midpoint  or data[r_shoulder] < l_midpoint:
        return None

    # Symmetry rule. time from shoulder to head are comparable
    r_to_h_time = r_shoulder - head
    l_to_h_time = head - l_shoulder
    if r_to_h_time > 2.5 * l_to_h_time or l_to_h_time > 2.5 * r_to_h_time:
        return None
        
    # Compute neckline
    neck_run = r_armpit - l_armpit
    neck_rise = data[r_armpit] - data[l_armpit]
    neck_slope = neck_rise / neck_run
    
    # neckline value at current index
    neck_val = data[l_armpit] + (i - l_armpit) * neck_slope

    # Confirm pattern when price is halfway from right shoulder
    if early_find: 
        if data[i] > r_midpoint:
            return None
    else:
       
        # Price has yet to break neckline, unconfirmed
        if data[i] > neck_val:
            return None

    # Find beginning of pattern. Neck to left shoulder
    head_width = r_armpit - l_armpit
    pat_start = -1
    neck_start = -1
    for j in range(1, head_width):
        neck = data[l_armpit] + (l_shoulder - l_armpit - j) * neck_slope
        
        if l_shoulder - j < 0:
            return None
        
        if data[l_shoulder - j] < neck:
            pat_start = l_shoulder - j
            neck_start = neck
            break

    if pat_start == -1:
        return None

    # Pattern confirmed if here :)
    pat = HSPattern(inverted=False)  
    
    pat.l_shoulder = l_shoulder
    pat.r_shoulder = r_shoulder
    pat.l_armpit = l_armpit
    pat.r_armpit = r_armpit
    pat.head = head
    
    pat.l_shoulder_p = data[l_shoulder]
    pat.r_shoulder_p = data[r_shoulder]
    pat.l_armpit_p = data[l_armpit]
    pat.r_armpit_p = data[r_armpit]
    pat.head_p = data[head]

    pat.start_i = pat_start
    pat.break_i = i
    pat.break_p = data[i]

    pat.neck_start = neck_start
    pat.neck_end = neck_val

    pat.neck_slope = neck_slope
    pat.head_width = head_width
    pat.head_height = data[head] - (data[l_armpit] + (head - l_armpit) * neck_slope)
    pat.pattern_r2 = compute_pattern_r2(data, pat)

    if pat.pattern_r2 <= 0.5:
        return None

    # I experiemented with r-squared as a filter for H&S, but this can delay recognition.
    # It didn't seem terribly potent, may be useful as a filter in conjunction with other attributes
    # if one wanted to add a machine learning layer before trading these patterns. 

    #if pat.pattern_r2 < 0.0:
    #    return None

    return pat

def ihs(extrema_indices: List[int], data: np.array, i:int, early_find: bool = False) -> HSPattern:
    
    # Unpack list
    l_shoulder = extrema_indices[0]
    l_armpit = extrema_indices[1]
    head = extrema_indices[2]
    r_armpit = extrema_indices[3]
    
    if i - r_armpit < 2:
        return None

    # Find right shoulder as max price since r_armpit
    r_shoulder = r_armpit + data[r_armpit+1: i].argmin() + 1

    # Head must be lower than shoulders
    if data[head] >= min(data[l_shoulder], data[r_shoulder]):
        return None

    # Balance rule. Shoulders are below the others midpoint.
    # A shoulder's midpoint is the midpoint between the shoulder and armpit
    r_midpoint = 0.5 * (data[r_shoulder] + data[r_armpit])
    l_midpoint = 0.5 * (data[l_shoulder] + data[l_armpit])
    if data[l_shoulder] > r_midpoint  or data[r_shoulder] > l_midpoint:
        return None

    # Symmetry rule. time from shoulder to head are comparable
    r_to_h_time = r_shoulder - head
    l_to_h_time = head - l_shoulder
    if r_to_h_time > 2.5 * l_to_h_time or l_to_h_time > 2.5 * r_to_h_time:
        return None

    # Compute neckline
    neck_run = r_armpit - l_armpit
    neck_rise = data[r_armpit] - data[l_armpit]
    neck_slope = neck_rise / neck_run
    
    # neckline value at current index
    neck_val = data[l_armpit] + (i - l_armpit) * neck_slope
    
    # Confirm pattern when price is halfway from right shoulder
    if early_find: 
        if data[i] < r_midpoint:
            return None
    else:
       
        # Price has yet to break neckline, unconfirmed
        if data[i] < neck_val:
            return None
   
    # Find beginning of pattern. Neck to left shoulder
    head_width = r_armpit - l_armpit
    pat_start = -1
    neck_start = -1
    for j in range(1, head_width):
        neck = data[l_armpit] + (l_shoulder - l_armpit - j) * neck_slope
        
        if l_shoulder - j < 0:
            return None
        
        if data[l_shoulder - j] > neck:
            pat_start = l_shoulder - j
            neck_start = neck
            break

    if pat_start == -1:
        return None

    # Pattern confirmed if here :)
    pat = HSPattern(inverted=True)  
    
    pat.l_shoulder = l_shoulder
    pat.r_shoulder = r_shoulder
    pat.l_armpit = l_armpit
    pat.r_armpit = r_armpit
    pat.head = head
    
    pat.l_shoulder_p = data[l_shoulder]
    pat.r_shoulder_p = data[r_shoulder]
    pat.l_armpit_p = data[l_armpit]
    pat.r_armpit_p = data[r_armpit]
    pat.head_p = data[head]

    pat.start_i = pat_start
    pat.break_i = i
    pat.break_p = data[i]

    pat.neck_start = neck_start
    pat.neck_end = neck_val
    pat.pattern_r2 = compute_pattern_r2(data, pat)
    
    pat.neck_slope = neck_slope
    pat.head_width = head_width
    pat.head_height = (data[l_armpit] + (head - l_armpit) * neck_slope) - data[head]
    pat.pattern_r2 = compute_pattern_r2(data, pat)
    
    if pat.pattern_r2 <= 0.5:
        return None
    #if pat.pattern_r2 < 0.0:
    #    return None

    return pat

def dt(extrema_indices: List[int], data: np.array, i:int, early_find: bool = False) -> HSPattern:
    ''' Returns a HSPattern if found, or None if not found ''' 
    # Unpack list
    l_shoulder = extrema_indices[0]
    l_armpit = extrema_indices[1]
    head = extrema_indices[2]
    r_armpit = extrema_indices[3]

    if i - r_armpit < 2:
        return None

    # Find right shoulder as max price since r_armpit
    r_shoulder = r_armpit + data[r_armpit + 1: i].argmax() + 1

    # Head must be higher than shoulders
    # if data[head] <= max(data[l_shoulder], data[r_shoulder]):
    #     return None
    
    # Head must be same as right shoulder
    diff = abs(data[head] - data[r_shoulder])
    min_peak = min(data[head], data[r_shoulder])
    if not (((diff/min_peak) <= 0.04)):
        return None

    # Balance rule. Shoulders are above the others midpoint.
    # A shoulder's midpoint is the midpoint between the shoulder and armpit
    r_midpoint = 0.5 * (data[r_shoulder] + data[r_armpit])
    # l_midpoint = 0.5 * (data[l_shoulder] + data[l_armpit])
    # if data[l_shoulder] < r_midpoint  or data[r_shoulder] < l_midpoint:
    #     return None
    # if not (data[r_shoulder] > data[l_shoulder]):
    #     return None

    # Symmetry rule. time from shoulder to head are comparable
    # r_to_h_time = r_shoulder - head
    # l_to_h_time = head - l_shoulder
    # if r_to_h_time > 2.5 * l_to_h_time or l_to_h_time > 2.5 * r_to_h_time:
    #     return None

    # depth rule. There should be at least a 10 % decline between the two tops
    t1_minus_p1 = data[r_armpit] - data[head] 
    if not ((t1_minus_p1/data[head]) <= -0.06):
        return None

        
    # Compute neckline
    neck_run = r_armpit - l_armpit
    neck_rise = data[r_armpit] - data[l_armpit]
    neck_slope = neck_rise / neck_run
    
    # neckline value at current index
    neck_val = data[l_armpit] + (i - l_armpit) * neck_slope

    # Confirm pattern when price is halfway from right shoulder
    if early_find: 
        if data[i] > r_midpoint:
            return None
    else:
       
        # Price has yet to break neckline, unconfirmed
        # if data[i] > neck_val:
        #     return None
        if data[i] > data[r_armpit]:
            return None

    # Find beginning of pattern. Neck to left shoulder
    head_width = r_armpit - l_armpit
    pat_start = -1
    neck_start = -1
    for j in range(1, head_width):
        neck = data[l_armpit] + (l_shoulder - l_armpit - j) * neck_slope
        
        if l_shoulder - j < 0:
            return None
        
        if data[l_shoulder - j] < neck:
            pat_start = l_shoulder - j
            neck_start = neck
            break

    if pat_start == -1:
        return None

    # Pattern confirmed if here :)
    pat = HSPattern(inverted=False)  
    
    pat.l_shoulder = l_shoulder
    pat.r_shoulder = r_shoulder
    pat.l_armpit = l_armpit
    pat.r_armpit = r_armpit
    pat.head = head
    
    pat.l_shoulder_p = data[l_shoulder]
    pat.r_shoulder_p = data[r_shoulder]
    pat.l_armpit_p = data[l_armpit]
    pat.r_armpit_p = data[r_armpit]
    pat.head_p = data[head]

    pat.start_i = pat_start
    pat.break_i = i
    pat.break_p = data[i]

    pat.neck_start = neck_start
    pat.neck_end = neck_val

    pat.neck_slope = neck_slope
    pat.head_width = head_width
    pat.head_height = data[head] - (data[l_armpit] + (head - l_armpit) * neck_slope)
    pat.pattern_r2 = compute_pattern_r2(data, pat)

    # I experiemented with r-squared as a filter for H&S, but this can delay recognition.
    # It didn't seem terribly potent, may be useful as a filter in conjunction with other attributes
    # if one wanted to add a machine learning layer before trading these patterns. 

    if pat.pattern_r2 <= 0.5:
        return None
    #if pat.pattern_r2 < 0.0:
    #    return None

    return pat

def db(extrema_indices: List[int], data: np.array, i:int, early_find: bool = False) -> HSPattern:
    
    # Unpack list
    l_shoulder = extrema_indices[0]
    l_armpit = extrema_indices[1]
    head = extrema_indices[2]
    r_armpit = extrema_indices[3]
    
    if i - r_armpit < 2:
        return None

    # Find right shoulder as max price since r_armpit
    r_shoulder = r_armpit + data[r_armpit+1: i].argmin() + 1

    # Head must be lower than shoulders
    # if data[head] >= min(data[l_shoulder], data[r_shoulder]):
    #     return None

    # Head must be same as right shoulder
    diff = abs(data[head] - data[r_shoulder])
    min_peak = min(data[head], data[r_shoulder])
    if not (((diff/min_peak) <= 0.04)):
        return None

    # # Balance rule. Shoulders are below the others midpoint.
    # # A shoulder's midpoint is the midpoint between the shoulder and armpit
    r_midpoint = 0.5 * (data[r_shoulder] + data[r_armpit])
    # l_midpoint = 0.5 * (data[l_shoulder] + data[l_armpit])
    # if data[l_shoulder] > r_midpoint  or data[r_shoulder] > l_midpoint:
    #     return None

    # Symmetry rule. time from shoulder to head are comparable
    # r_to_h_time = r_shoulder - head
    # l_to_h_time = head - l_shoulder
    # if r_to_h_time > 2.5 * l_to_h_time or l_to_h_time > 2.5 * r_to_h_time:
    #     return None

    # depth rule. There should be at least a 10 % decline between the two tops
    t1_minus_p1 = data[r_armpit] - data[head] 
    if not ((t1_minus_p1/data[head]) >= 0.06):
        return None

    # Compute neckline
    neck_run = r_armpit - l_armpit
    neck_rise = data[r_armpit] - data[l_armpit]
    neck_slope = neck_rise / neck_run
    
    # neckline value at current index
    neck_val = data[l_armpit] + (i - l_armpit) * neck_slope
    
    # Confirm pattern when price is halfway from right shoulder
    if early_find: 
        if data[i] < r_midpoint:
            return None
    else:
       
        # Price has yet to break neckline, unconfirmed
        if data[i] < neck_val:
            return None
   
    # Find beginning of pattern. Neck to left shoulder
    head_width = r_armpit - l_armpit
    pat_start = -1
    neck_start = -1
    for j in range(1, head_width):
        neck = data[l_armpit] + (l_shoulder - l_armpit - j) * neck_slope
        
        if l_shoulder - j < 0:
            return None
        
        if data[l_shoulder - j] > neck:
            pat_start = l_shoulder - j
            neck_start = neck
            break

    if pat_start == -1:
        return None

    # Pattern confirmed if here :)
    pat = HSPattern(inverted=True)  
    
    pat.l_shoulder = l_shoulder
    pat.r_shoulder = r_shoulder
    pat.l_armpit = l_armpit
    pat.r_armpit = r_armpit
    pat.head = head
    
    pat.l_shoulder_p = data[l_shoulder]
    pat.r_shoulder_p = data[r_shoulder]
    pat.l_armpit_p = data[l_armpit]
    pat.r_armpit_p = data[r_armpit]
    pat.head_p = data[head]

    pat.start_i = pat_start
    pat.break_i = i
    pat.break_p = data[i]

    pat.neck_start = neck_start
    pat.neck_end = neck_val
    pat.pattern_r2 = compute_pattern_r2(data, pat)
    
    pat.neck_slope = neck_slope
    pat.head_width = head_width
    pat.head_height = (data[l_armpit] + (head - l_armpit) * neck_slope) - data[head]
    pat.pattern_r2 = compute_pattern_r2(data, pat)
    
    if pat.pattern_r2 <= 0.5:
        return None
    #if pat.pattern_r2 < 0.0:
    #    return None

    return pat

def tt(extrema_indices: List[int], data: np.array, i:int, early_find: bool = False) -> HSPattern:
    ''' Returns a HSPattern if found, or None if not found ''' 
    # Unpack list
    l_shoulder = extrema_indices[0]
    l_armpit = extrema_indices[1]
    head = extrema_indices[2]
    r_armpit = extrema_indices[3]

    if i - r_armpit < 2:
        return None

    # Find right shoulder as max price since r_armpit
    r_shoulder = r_armpit + data[r_armpit + 1: i].argmax() + 1

    # Head must be higher than shoulders
    # if data[head] <= max(data[l_shoulder], data[r_shoulder]):
    #     return None

    # Balance rule. Shoulders are above the others midpoint.
    # A shoulder's midpoint is the midpoint between the shoulder and armpit
    r_midpoint = 0.5 * (data[r_shoulder] + data[r_armpit])
    # l_midpoint = 0.5 * (data[l_shoulder] + data[l_armpit])
    # if data[l_shoulder] < r_midpoint  or data[r_shoulder] < l_midpoint:
    #     return None

    # Symmetry rule. time from shoulder to head are comparable
    # r_to_h_time = r_shoulder - head
    # l_to_h_time = head - l_shoulder
    # if r_to_h_time > 2.5 * l_to_h_time or l_to_h_time > 2.5 * r_to_h_time:
    #     return None

    # Balance:Three peaks (bottoms) are about the same level.
    if not (((max(data[l_shoulder], data[r_shoulder]) - min(data[l_shoulder], data[r_shoulder]))/min(data[l_shoulder], data[r_shoulder])) <= 0.04  and data[head] <= max(data[l_shoulder], data[r_shoulder])):
        return None
    
    # Intervening locals
    if not (data[l_armpit] <= data[r_armpit] <= (data[l_armpit]*1.04)):
        return None
        
    # Compute neckline
    neck_run = r_armpit - l_armpit
    neck_rise = data[r_armpit] - data[l_armpit]
    neck_slope = neck_rise / neck_run
    
    # neckline value at current index
    neck_val = data[l_armpit] + (i - l_armpit) * neck_slope

    # Confirm pattern when price is halfway from right shoulder
    if early_find: 
        if data[i] > r_midpoint:
            return None
    else:
       
        # Price has yet to break neckline, unconfirmed
        if data[i] > neck_val:
            return None

    # Find beginning of pattern. Neck to left shoulder
    head_width = r_armpit - l_armpit
    pat_start = -1
    neck_start = -1
    for j in range(1, head_width):
        neck = data[l_armpit] + (l_shoulder - l_armpit - j) * neck_slope
        
        if l_shoulder - j < 0:
            return None
        
        if data[l_shoulder - j] < neck:
            pat_start = l_shoulder - j
            neck_start = neck
            break

    if pat_start == -1:
        return None

    # Pattern confirmed if here :)
    pat = HSPattern(inverted=False)  
    
    pat.l_shoulder = l_shoulder
    pat.r_shoulder = r_shoulder
    pat.l_armpit = l_armpit
    pat.r_armpit = r_armpit
    pat.head = head
    
    pat.l_shoulder_p = data[l_shoulder]
    pat.r_shoulder_p = data[r_shoulder]
    pat.l_armpit_p = data[l_armpit]
    pat.r_armpit_p = data[r_armpit]
    pat.head_p = data[head]

    pat.start_i = pat_start
    pat.break_i = i
    pat.break_p = data[i]

    pat.neck_start = neck_start
    pat.neck_end = neck_val

    pat.neck_slope = neck_slope
    pat.head_width = head_width
    pat.head_height = data[head] - (data[l_armpit] + (head - l_armpit) * neck_slope)
    pat.pattern_r2 = compute_pattern_r2(data, pat)

    # I experiemented with r-squared as a filter for H&S, but this can delay recognition.
    # It didn't seem terribly potent, may be useful as a filter in conjunction with other attributes
    # if one wanted to add a machine learning layer before trading these patterns. 

    if pat.pattern_r2 <= 0.5:
        return None
    #if pat.pattern_r2 < 0.0:
    #    return None

    return pat

def tb(extrema_indices: List[int], data: np.array, i:int, early_find: bool = False) -> HSPattern:
    
    # Unpack list
    l_shoulder = extrema_indices[0]
    l_armpit = extrema_indices[1]
    head = extrema_indices[2]
    r_armpit = extrema_indices[3]
    
    if i - r_armpit < 2:
        return None

    # Find right shoulder as max price since r_armpit
    r_shoulder = r_armpit + data[r_armpit+1: i].argmin() + 1

    # Head must be lower than shoulders
    # if data[head] >= min(data[l_shoulder], data[r_shoulder]):
    #     return None

    # Balance rule. Shoulders are below the others midpoint.
    # A shoulder's midpoint is the midpoint between the shoulder and armpit
    r_midpoint = 0.5 * (data[r_shoulder] + data[r_armpit])
    # l_midpoint = 0.5 * (data[l_shoulder] + data[l_armpit])
    # if data[l_shoulder] > r_midpoint  or data[r_shoulder] > l_midpoint:
    #     return None

    # Symmetry rule. time from shoulder to head are comparable
    # r_to_h_time = r_shoulder - head
    # l_to_h_time = head - l_shoulder
    # if r_to_h_time > 2.5 * l_to_h_time or l_to_h_time > 2.5 * r_to_h_time:
    #     return None

    # Balance:Three peaks (bottoms) are about the same level.
    if not (((max(data[l_shoulder], data[r_shoulder]) - min(data[l_shoulder], data[r_shoulder]))/min(data[l_shoulder], data[r_shoulder])) <= 0.04  and data[head] >= min(data[l_shoulder], data[r_shoulder])):
        return None

    # Intervening locals
    if not (data[l_armpit] <= data[r_armpit] <= (data[l_armpit]*1.04)):
        return None

    # Compute neckline
    neck_run = r_armpit - l_armpit
    neck_rise = data[r_armpit] - data[l_armpit]
    neck_slope = neck_rise / neck_run
    
    # neckline value at current index
    neck_val = data[l_armpit] + (i - l_armpit) * neck_slope
    
    # Confirm pattern when price is halfway from right shoulder
    if early_find: 
        if data[i] < r_midpoint:
            return None
    else:
       
        # Price has yet to break neckline, unconfirmed
        if data[i] < neck_val:
            return None
   
    # Find beginning of pattern. Neck to left shoulder
    head_width = r_armpit - l_armpit
    pat_start = -1
    neck_start = -1
    for j in range(1, head_width):
        neck = data[l_armpit] + (l_shoulder - l_armpit - j) * neck_slope
        
        if l_shoulder - j < 0:
            return None
        
        if data[l_shoulder - j] > neck:
            pat_start = l_shoulder - j
            neck_start = neck
            break

    if pat_start == -1:
        return None

    # Pattern confirmed if here :)
    pat = HSPattern(inverted=True)  
    
    pat.l_shoulder = l_shoulder
    pat.r_shoulder = r_shoulder
    pat.l_armpit = l_armpit
    pat.r_armpit = r_armpit
    pat.head = head
    
    pat.l_shoulder_p = data[l_shoulder]
    pat.r_shoulder_p = data[r_shoulder]
    pat.l_armpit_p = data[l_armpit]
    pat.r_armpit_p = data[r_armpit]
    pat.head_p = data[head]

    pat.start_i = pat_start
    pat.break_i = i
    pat.break_p = data[i]

    pat.neck_start = neck_start
    pat.neck_end = neck_val
    pat.pattern_r2 = compute_pattern_r2(data, pat)
    
    pat.neck_slope = neck_slope
    pat.head_width = head_width
    pat.head_height = (data[l_armpit] + (head - l_armpit) * neck_slope) - data[head]
    pat.pattern_r2 = compute_pattern_r2(data, pat)
    
    if pat.pattern_r2 <= 0.5:
        return None
    #if pat.pattern_r2 < 0.0:
    #    return None

    return pat

def hs_plt_plot(df: pd.DataFrame, pattern: HSPattern, pad: int=2):
    if pad < 0:
        pad = 0
    if pattern.pattern_r2<0:
        pattern.pattern_r2=0
    r2 = "{:.2f}%".format(pattern.pattern_r2 * 100)

    # Alternatively, using f-string (Python 3.6+)
    r2 = f"{pattern.pattern_r2 * 100:.2f}%"
    # r2 = str(pattern.pattern_r2*100) + "%"
    one, two = ('red', 'blue') if not pattern.inverted else ('blue', 'red')
    line_color = 'black'

    # plt.scatter(df['Date'].iloc[pattern.start_i], df['Close'].iloc[pattern.start_i], color=one, zorder=5, s=.5)
    # plt.scatter(df['Date'].iloc[pattern.l_shoulder], df['Close'].iloc[pattern.l_shoulder], color=two, zorder=5, s=.5)
    # plt.scatter(df['Date'].iloc[pattern.l_armpit], df['Close'].iloc[pattern.l_armpit], color=one, zorder=5, s=.5)
    # plt.scatter(df['Date'].iloc[pattern.head], df['Close'].iloc[pattern.head], color=two, zorder=5, s=.5)
    # plt.scatter(df['Date'].iloc[pattern.r_armpit], df['Close'].iloc[pattern.r_armpit], color=one, zorder=5, s=.5)
    # plt.scatter(df['Date'].iloc[pattern.r_shoulder], df['Close'].iloc[pattern.r_shoulder], color=two, zorder=5, s=.5)
    # plt.scatter(df['Date'].iloc[pattern.break_i], df['Close'].iloc[pattern.break_i], color=one, zorder=5, s=.5)
    

    # plt.text(pd.Timestamp(str(df['Date'].iloc[pattern.break_i])), df['Close'].iloc[pattern.break_i], r2, fontsize=12, ha='center', va='center')
    # x_text = df['Date'].iloc[pattern.start_i]  # Midpoint X
    # y_text = df['Close'].iloc[pattern.start_i]   # Midpoint Y + offset

    # Display "abcd" above the line
    # plt.text(x_text, y_text, r2, fontsize=1, ha='center', va='bottom')
    # plt.figtext(x_text, y_text, r2, fontsize=12, ha='center')

    plt.plot([df['Date'].iloc[pattern.start_i], df['Date'].iloc[pattern.l_shoulder]], 
             [df['Close'].iloc[pattern.start_i], df['Close'].iloc[pattern.l_shoulder]], 
             color=line_color, linewidth=2)

    plt.plot([df['Date'].iloc[pattern.l_shoulder], df['Date'].iloc[pattern.l_armpit]], 
             [df['Close'].iloc[pattern.l_shoulder], df['Close'].iloc[pattern.l_armpit]], 
             color=line_color, linewidth=2)

    plt.plot([df['Date'].iloc[pattern.l_armpit], df['Date'].iloc[pattern.head]], 
             [df['Close'].iloc[pattern.l_armpit], df['Close'].iloc[pattern.head]], 
             color=line_color, linewidth=2)

    plt.plot([df['Date'].iloc[pattern.head], df['Date'].iloc[pattern.r_armpit]], 
             [df['Close'].iloc[pattern.head], df['Close'].iloc[pattern.r_armpit]], 
             color=line_color, linewidth=2)

    plt.plot([df['Date'].iloc[pattern.r_armpit], df['Date'].iloc[pattern.r_shoulder]], 
             [df['Close'].iloc[pattern.r_armpit], df['Close'].iloc[pattern.r_shoulder]], 
             color=line_color, linewidth=2)

    plt.plot([df['Date'].iloc[pattern.r_shoulder], df['Date'].iloc[pattern.break_i]], 
             [df['Close'].iloc[pattern.r_shoulder], df['Close'].iloc[pattern.break_i]], 
             color=line_color, linewidth=2)

    plt.plot([df['Date'].iloc[pattern.start_i], df['Date'].iloc[pattern.break_i]], 
             [df['Close'].iloc[pattern.start_i], df['Close'].iloc[pattern.break_i]], 
             linewidth=2, label=r2)

ihs_plt_plot = hs_plt_plot

def dt_plt_plot(df: pd.DataFrame, pattern: HSPattern, pad: int=2):
    if pad < 0:
        pad = 0

    if pattern.pattern_r2<0:
        pattern.pattern_r2=0
    r2 = "{:.2f}%".format(pattern.pattern_r2 * 100)

    # Alternatively, using f-string (Python 3.6+)
    r2 = f"{pattern.pattern_r2 * 100:.2f}%"

    one, two = ('red', 'blue') if not pattern.inverted else ('blue', 'red')
    line_color = 'black'

    # plt.scatter(df['Date'].iloc[pattern.start_i], df['Close'].iloc[pattern.start_i], color=one, zorder=5)
    # plt.scatter(df['Date'].iloc[pattern.l_shoulder], df['Close'].iloc[pattern.l_shoulder], color=two, zorder=5)
    # plt.scatter(df['Date'].iloc[pattern.l_armpit], df['Close'].iloc[pattern.l_armpit], color=one, zorder=5)
    # plt.scatter(df['Date'].iloc[pattern.head], df['Close'].iloc[pattern.head], color=two, zorder=5)
    # plt.scatter(df['Date'].iloc[pattern.r_armpit], df['Close'].iloc[pattern.r_armpit], color=one, zorder=5)
    # plt.scatter(df['Date'].iloc[pattern.r_shoulder], df['Close'].iloc[pattern.r_shoulder], color=two, zorder=5)
    # plt.scatter(df['Date'].iloc[pattern.break_i], df['Close'].iloc[pattern.break_i], color=one, zorder=5)
    

    # plt.plot([df['Date'].iloc[pattern.start_i], df['Date'].iloc[pattern.l_shoulder]], 
    #          [df['Close'].iloc[pattern.start_i], df['Close'].iloc[pattern.l_shoulder]], 
    #          color=line_color, linewidth=2)

    # plt.plot([df['Date'].iloc[pattern.l_shoulder], df['Date'].iloc[pattern.l_armpit]], 
    #          [df['Close'].iloc[pattern.l_shoulder], df['Close'].iloc[pattern.l_armpit]], 
    #          color=line_color, linewidth=2)

    x_text = df['Date'].iloc[pattern.start_i]  # Midpoint X
    y_text = df['Close'].iloc[pattern.start_i]   # Midpoint Y + offset

    # Display "abcd" above the line
    plt.text(x_text, y_text, r2, fontsize=1, ha='center', va='bottom')
    plt.plot([df['Date'].iloc[pattern.l_armpit], df['Date'].iloc[pattern.head]], 
             [df['Close'].iloc[pattern.l_armpit], df['Close'].iloc[pattern.head]], 
             color=line_color, linewidth=2)

    plt.plot([df['Date'].iloc[pattern.head], df['Date'].iloc[pattern.r_armpit]], 
             [df['Close'].iloc[pattern.head], df['Close'].iloc[pattern.r_armpit]], 
             color=line_color, linewidth=2)

    plt.plot([df['Date'].iloc[pattern.r_armpit], df['Date'].iloc[pattern.r_shoulder]], 
             [df['Close'].iloc[pattern.r_armpit], df['Close'].iloc[pattern.r_shoulder]], 
             color=line_color, linewidth=2)

    plt.plot([df['Date'].iloc[pattern.r_shoulder], df['Date'].iloc[pattern.break_i]], 
             [df['Close'].iloc[pattern.r_shoulder], df['Close'].iloc[pattern.break_i]], 
             color=line_color, linewidth=2)

    plt.plot([df['Date'].iloc[pattern.l_armpit], df['Date'].iloc[pattern.break_i]], 
             [df['Close'].iloc[pattern.l_armpit], df['Close'].iloc[pattern.break_i]], 
            linewidth=2)

db_plt_plot = dt_plt_plot
tt_plt_plot = hs_plt_plot
tb_plt_plot = hs_plt_plot

pattern_algo = {
    "Head-&-Shoulders" : (hs, hs_plt_plot),
    "Inverse Head-&-Shoulders" : (ihs, ihs_plt_plot),
    "Double Top" : (dt, dt_plt_plot),
    "Double Bottom" : (db, db_plt_plot),
    "Tripple Top" : (tt, tt_plt_plot),
    "Tripple Bottom" : (tb, tb_plt_plot),
}

def find_patterns(data: np.array, order:int, early_find:bool = False, pattern_name: str = ''):
    assert(order >= 1)
    
    # head and shoulders top checked from/after a confirmed bottom (before right shoulder)
    # head and shoulders bottom checked from/after a confirmed top 
    
    last_is_top = False
    recent_extrema = deque(maxlen=5)
    recent_types = deque(maxlen=5) # -1 for bottoms 1 for tops

    # Lock variables to prevent finding the same pattern multiple times
    hs_lock = False
    ihs_lock = False

    ihs_patterns = [] # Inverted (bullish)
    hs_patterns = []  # Regular (bearish)
    for i in range(len(data)):

        if rw_top(data, i, order):
            recent_extrema.append(i - order)
            recent_types.append(1)
            ihs_lock = False
            last_is_top = True
        
        if rw_bottom(data, i, order):
            recent_extrema.append(i - order)
            recent_types.append(-1)
            hs_lock = False
            last_is_top = False

        if len(recent_extrema) < 5:
            continue
        
        hs_alternating = True
        ihs_alternating = True
        
        if last_is_top:
            for j in range(2, 5):
                if recent_types[j] == recent_types[j - 1]: 
                    ihs_alternating = False
            
            for j in range(1, 4):
                if recent_types[j] == recent_types[j - 1]: 
                    hs_alternating = False
            
            ihs_extrema = list(recent_extrema)[1:5]
            hs_extrema = list(recent_extrema)[0:4]
        else:
            
            for j in range(2, 5):
                if recent_types[j] == recent_types[j - 1]: 
                    hs_alternating = False
            
            for j in range(1, 4):
                if recent_types[j] == recent_types[j - 1]: 
                    ihs_alternating = False
            
            ihs_extrema = list(recent_extrema)[0:4]
            hs_extrema = list(recent_extrema)[1:5]
        
        if ihs_lock or not ihs_alternating:
            ihs_pat = None
        else:
            ihs_pat = pattern_algo[pattern_name][0](ihs_extrema, data, i, early_find)

        if hs_lock or not hs_alternating:
            hs_pat = None
        else:
            hs_pat = pattern_algo[pattern_name][0](hs_extrema, data, i, early_find)

        if hs_pat is not None:
            hs_lock = True
            hs_patterns.append(hs_pat)
        
        if ihs_pat is not None:
            ihs_lock = True
            ihs_patterns.append(ihs_pat)


    return hs_patterns, ihs_patterns


def get_pattern_return(data: np.array, pat: HSPattern, log_prices: bool = True) -> float:

    entry_price = pat.break_p
    entry_i = pat.break_i
    stop_price = pat.r_shoulder_p

    if pat.inverted:
        tp_price = pat.neck_end + pat.head_height
    else:
        tp_price = pat.neck_end - pat.head_height

    exit_price = -1
    for i in range(pat.head_width):
        if entry_i + i >= len(data):
            return np.nan

        exit_price = data[entry_i + i]
        if pat.inverted and (exit_price > tp_price or exit_price < stop_price):
            break
        
        if not pat.inverted and (exit_price < tp_price or exit_price > stop_price):
            break
    
    if pat.inverted: # Long
        if log_prices:
            return exit_price - entry_price
        else:
            return (exit_price - entry_price) / entry_price
    else: # Short
        if log_prices:
            return entry_price - exit_price
        else:
            return -1 * (exit_price - entry_price) / entry_price



tooltip_css = """
table
{
  border-collapse: collapse;
}
th
{
  color: #ffffff;
  background-color: #000000;
}
td
{
  background-color: #cccccc;
}
table, th, td
{
  font-family:Arial, Helvetica, sans-serif;
  border: 1px solid black;
  text-align: right;
}
"""



def get_chart(symbol: str, pattern_name: str):
    df = get_data_by_symbol(database_path=current_app.config['DB_PATH'], symbol=symbol)
    df['Date'] = pd.to_datetime(df['Date'])
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    # df['Date'] = df['Date'].astype(int) // 10**9  # Convert nanoseconds to seconds
    
    arr = df['Close'].to_numpy()
    # order = 15


    fig = plt.figure(figsize=(12, 6))
    points = plt.plot(df['Date'], df['Close'], color='#1DAE1A', label='Close Price')
    plt.fill_between(df['Date'], df['Close'], color='#1DAE1A', alpha=0.3)
    
    
    labels = []
    for i in range(len(df['Date'])):
        label = df.iloc[[i], :].T
        label.columns = ['Row {0}'.format(i)]
        # .to_html() is unicode; so make leading 'u' go away with str()
        labels.append(str(label.to_html()))

    # tooltip = plugins.PointHTMLTooltip(points[0], labels,  voffset=10, hoffset=10, css=tooltip_css)

    for order in range(2, 90):
        hs_patterns, ihs_patterns = find_patterns(arr, order=order, early_find=False, pattern_name=pattern_name)
        for pattern in hs_patterns:
            pattern_algo[pattern_name][1](df, pattern)
    
    plt.title(symbol)
    plt.legend()
    plt.grid()
    plt.tight_layout()

    # plt.show()
    # plugins.connect(fig, tooltip)
    return mpld3.fig_to_html(fig)

# get_chart('HDFCBANK', 'Head-&-Shoulders')