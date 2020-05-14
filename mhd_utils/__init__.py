# Original Version: bjian 2008/10/27
# 3-D extension:    PJackson 2013/06/06        
# More datatypes, Multiple Channels, Python 3, ...: Peter Fischer

from __future__ import division, print_function
from typing import Dict, Tuple, Any
from os import PathLike
import sys
from pathlib import Path

import numpy as np


def read_meta_header(filename: PathLike) -> Dict[str, Any]:
    """
    Return a dictionary of meta data from MHD meta header file
    
    :param filename: file of type .mhd that should be loaded
    :returns: dictionary of meta data
    """
    
    # Define tags
    meta_dict = {}
    tag_set = []
    tag_set.extend(['ObjectType', 'NDims', 'DimSize', 'ElementType', 'ElementDataFile', 'ElementNumberOfChannels'])
    tag_set.extend(['BinaryData', 'BinaryDataByteOrderMSB', 'CompressedData', 'CompressedDataSize'])
    tag_set.extend(['Offset', 'CenterOfRotation', 'AnatomicalOrientation', 'ElementSpacing', 'TransformMatrix'])
    tag_set.extend(['Comment', 'SeriesDescription', 'AcquisitionDate', 'AcquisitionTime', 'StudyDate', 'StudyTime'])

    tag_flag = [False] * len(tag_set)

    with open(filename, "r") as fn:
        line = fn.readline()
        while line:
            tags = str.split(line, '=')
            # print(tags[0])
            for i in range(len(tag_set)):
                tag = tag_set[i]
                if (str.strip(tags[0]) == tag) and (not tag_flag[i]):
                    # print(tags[1])
                    content = str.strip(tags[1])
                    if tag in ['ElementSpacing', 'Offset', 'CenterOfRotation', 'TransformMatrix']:
                        meta_dict[tag] = [float(s) for s in content.split()]
                    elif tag in ['NDims', 'ElementNumberOfChannels']:
                        meta_dict[tag] = int(content)
                    elif tag in ['DimSize']:
                        meta_dict[tag] = [int(s) for s in content.split()]
                    elif tag in ['BinaryData', 'BinaryDataByteOrderMSB', 'CompressedData']:
                        if content == "True":
                            meta_dict[tag] = True
                        else:
                            meta_dict[tag] = False
                    else:
                        meta_dict[tag] = content
                    tag_flag[i] = True
            line = fn.readline()
    return meta_dict


def load_raw_data_with_mhd(filename: PathLike) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Load a MHD file

    :param filename: file of type .mhd that should be loaded
    :returns: tuple with raw data and dictionary of meta data
    """
    meta_dict = read_meta_header(filename)
    dim = int(meta_dict['NDims'])
    if "ElementNumberOfChannels" in meta_dict:
        element_channels = int(meta_dict["ElementNumberOfChannels"])
    else:
        element_channels = 1

    if meta_dict['ElementType'] == 'MET_FLOAT':
        np_type = np.float32
    elif meta_dict['ElementType'] == 'MET_DOUBLE':
        np_type = np.float64
    elif meta_dict['ElementType'] == 'MET_CHAR':
        np_type = np.byte
    elif meta_dict['ElementType'] == 'MET_UCHAR':
        np_type = np.ubyte
    elif meta_dict['ElementType'] == 'MET_SHORT':
        np_type = np.short
    elif meta_dict['ElementType'] == 'MET_USHORT':
        np_type = np.ushort
    elif meta_dict['ElementType'] == 'MET_INT':
        np_type = np.int32
    elif meta_dict['ElementType'] == 'MET_UINT':
        np_type = np.uint32
    else:
        raise NotImplementedError("ElementType " + meta_dict['ElementType'] + " not understood.")
    arr = list(meta_dict['DimSize'])

    volume = np.prod(arr[0:dim - 1])

    pwd = Path(filename).parents[0]
    data_file = Path(meta_dict['ElementDataFile'])
    if not data_file.is_absolute():
        data_file = pwd / data_file

    shape = (arr[dim - 1], volume, element_channels)
    with open(data_file,'rb') as f:
        data = np.fromfile(f, count=np.prod(shape), dtype=np_type)
    data.shape = shape

    # Adjust byte order in numpy array to match default system byte order
    if 'BinaryDataByteOrderMSB' in meta_dict:
        sys_byteorder_msb = sys.byteorder == 'big'
        file_byteorder_ms =  meta_dict['BinaryDataByteOrderMSB']
        if sys_byteorder_msb != file_byteorder_ms:
            data = data.byteswap()

    # Begin 3D fix
    arr.reverse()
    if element_channels > 1:
        data = data.reshape(arr + [element_channels])
    else:
        data = data.reshape(arr)
    # End 3D fix
    
    return (data, meta_dict)


def write_meta_header(filename: PathLike, meta_dict: Dict[str, Any]):
    """
    Write the MHD meta header file

    :param filename: file to write
    :param meta_dict: dictionary of meta data in MetaImage format
    """
    header = ''
    # do not use tags = meta_dict.keys() because the order of tags matters
    tags = ['ObjectType', 'NDims', 'BinaryData',
            'BinaryDataByteOrderMSB', 'CompressedData', 'CompressedDataSize',
            'TransformMatrix', 'Offset', 'CenterOfRotation',
            'AnatomicalOrientation', 'ElementSpacing',
            'DimSize', 'ElementNumberOfChannels', 'ElementType', 'ElementDataFile',
            'Comment', 'SeriesDescription', 'AcquisitionDate',
            'AcquisitionTime', 'StudyDate', 'StudyTime']
    for tag in tags:
        if tag in meta_dict.keys():
            header += '%s = %s\n' % (tag, meta_dict[tag])
    with open(filename, 'w') as f:
        f.write(header)


def write_mhd_file(filename: PathLike, data: np.ndarray, **meta_dict):
    """
    Write a meta file and the raw file.
    The byte order of the raw file will always be in the byte order of the system. 

    :param filename: file to write
    :param meta_dict: dictionary of meta data in MetaImage format
    """
    assert filename[-4:] == '.mhd' 
    meta_dict['ObjectType'] = 'Image'
    meta_dict['BinaryData'] = 'True'
    meta_dict['BinaryDataByteOrderMSB'] = 'False' if sys.byteorder == 'little' else 'True'
    if data.dtype == np.float32:
        meta_dict['ElementType'] = 'MET_FLOAT'
    elif data.dtype == np.double or data.dtype == np.float64:
        meta_dict['ElementType'] = 'MET_DOUBLE'
    elif data.dtype == np.byte:
        meta_dict['ElementType'] = 'MET_CHAR'
    elif data.dtype == np.uint8 or data.dtype == np.ubyte:
        meta_dict['ElementType'] = 'MET_UCHAR'
    elif data.dtype == np.short or data.dtype == np.int16:
        meta_dict['ElementType'] = 'MET_SHORT'
    elif data.dtype == np.ushort or data.dtype == np.uint16:
        meta_dict['ElementType'] = 'MET_USHORT'
    elif data.dtype == np.int32:
        meta_dict['ElementType'] = 'MET_INT'
    elif data.dtype == np.uint32:
        meta_dict['ElementType'] = 'MET_UINT'
    else:
        raise NotImplementedError("ElementType " + str(data.dtype) + " not implemented.")
    dsize = list(data.shape)
    if 'ElementNumberOfChannels' in meta_dict.keys():
        element_channels = int(meta_dict['ElementNumberOfChannels'])
        assert(dsize[-1] == element_channels)
        dsize = dsize[:-1]
    else:
        element_channels = 1
    dsize.reverse()
    meta_dict['NDims'] = str(len(dsize))
    meta_dict['DimSize'] = dsize
    meta_dict['ElementDataFile'] = str(Path(filename).name).replace('.mhd', '.raw')
    print(str(Path(filename).name).replace('.mhd', '.raw'))

    # Tags that need conversion of list to string
    tags = ['ElementSpacing', 'Offset', 'DimSize', 'CenterOfRotation', 'TransformMatrix']
    for tag in tags:
        if tag in meta_dict.keys() and not isinstance(meta_dict[tag], str):
            meta_dict[tag] = ' '.join([str(i) for i in meta_dict[tag]])
    write_meta_header(filename, meta_dict)

    # Compute absolute path to write to
    pwd = Path(filename).parents[0]
    data_file = Path(meta_dict['ElementDataFile'])
    if not data_file.is_absolute():
        data_file = pwd / data_file

    # Dump raw data
    data = data.reshape(dsize[0], -1, element_channels)
    with open(data_file, 'wb') as f:
        data.tofile(f)