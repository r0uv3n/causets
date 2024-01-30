#!/usr/bin/env python
'''
Created on 31 Jan 2024

@author: Henry Ruben Fischer
@license: BSD 3-Clause
'''

from typing import List, Dict, Any, Callable, Union, Optional
from matplotlib.pyplot import gca, subplot  # @UnusedImport
from mpl_toolkits.mplot3d.axes3d import Axes3D

def _getAxis(is3d: Optional[bool] = None):
    currentAxis = gca()
    if ((is3d is None) or
       (is3d and isinstance(currentAxis,Axes3D)) or
       (not is3d and not isinstance(currentAxis,Axes3D))):
        return currentAxis
    elif is3d:
        return subplot(projection='3d')
    else:
        return subplot(projection=None)
