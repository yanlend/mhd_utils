#!/usr/bin/env python

#
# Original Version: bjian 2008/10/27
# 3-D extension:    PJackson 2013/06/06        
# More datatypes, Multiple Channels, Python 3, ...: Peter Fischer
#

from __future__ import division, print_function
import os
import numpy
import array


def read_meta_header(filename):
    """Return a dictionary of meta data from meta header file"""
    fileIN = open(filename, "r")
    line = fileIN.readline()

    meta_dict = {}
    tag_set = []
    tag_set.extend(['ObjectType', 'NDims', 'DimSize', 'ElementType', 'ElementDataFile', 'ElementNumberOfChannels'])
    tag_set.extend(['BinaryData', 'BinaryDataByteOrderMSB', 'CompressedData', 'CompressedDataSize'])
    tag_set.extend(['Offset', 'CenterOfRotation', 'AnatomicalOrientation', 'ElementSpacing', 'TransformMatrix'])
    tag_set.extend(['Comment', 'SeriesDescription', 'AcquisitionDate', 'AcquisitionTime', 'StudyDate', 'StudyTime'])

    tag_flag = [False] * len(tag_set)
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
        line = fileIN.readline()
    # print(comment)
    fileIN.close()
    return meta_dict


def load_raw_data_with_mhd(filename):
    meta_dict = read_meta_header(filename)
    dim = int(meta_dict['NDims'])
    if "ElementNumberOfChannels" in meta_dict:
        element_channels = int(meta_dict["ElementNumberOfChannels"])
    else:
        element_channels = 1
    # print(dim)
    # print(meta_dict['ElementType'])
    if meta_dict['ElementType'] == 'MET_FLOAT':
        array_string = 'f'
        numpy_type = numpy.float32
    elif meta_dict['ElementType'] == 'MET_DOUBLE':
        array_string = 'd'
        numpy_type = numpy.float64
    elif meta_dict['ElementType'] == 'MET_CHAR':
        array_string = 'b'
        numpy_type = numpy.byte
    elif meta_dict['ElementType'] == 'MET_UCHAR':
        array_string = 'B'
        numpy_type = numpy.ubyte
    elif meta_dict['ElementType'] == 'MET_SHORT':
        array_string = 'h'
        numpy_type = numpy.short
    elif meta_dict['ElementType'] == 'MET_USHORT':
        array_string = 'H'
        numpy_type = numpy.ushort
    elif meta_dict['ElementType'] == 'MET_INT':
        array_string = 'i'
        numpy_type = numpy.int32
    elif meta_dict['ElementType'] == 'MET_UINT':
        array_string = 'I'
        numpy_type = numpy.uint32
    else:
        raise NotImplementedError("ElementType " + meta_dict['ElementType'] + " not understood.")
    arr = list(meta_dict['DimSize'])
    # print(arr)
    volume = numpy.prod(arr[0:dim - 1])
    # print(volume)
    pwd = os.path.split(filename)[0]
    if pwd:
        data_file = pwd + '/' + meta_dict['ElementDataFile']
    else:
        data_file = meta_dict['ElementDataFile']
    # print(data_file)
    fid = open(data_file, 'rb')
    binvalues = array.array(array_string)
    binvalues.fromfile(fid, volume * arr[dim - 1] * element_channels)
    fid.close()
    data = numpy.array(binvalues, numpy_type)
    data = numpy.reshape(data, (arr[dim - 1], volume, element_channels))
    # Begin 3D fix
    arr.reverse()
    if element_channels > 1:
        data = data.reshape(arr + [element_channels])
    else:
        data = data.reshape(arr)
    # End 3D fix
    return (data, meta_dict)


def write_meta_header(filename, meta_dict):
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
    f = open(filename, 'w')
    f.write(header)
    f.close()


def dump_raw_data(filename, data, dsize, element_channels=1):
    """ Write the data into a raw format file. Big endian is always used. """
    data = data.reshape(dsize[0], -1, element_channels)
    rawfile = open(filename, 'wb')
    if data.dtype == numpy.float32:
        array_string = 'f'
    elif data.dtype == numpy.double or data.dtype == numpy.float64:
        array_string = 'd'
    elif data.dtype == numpy.short:
        array_string = 'h'
    elif data.dtype == numpy.ushort:
        array_string = 'H'
    elif data.dtype == numpy.int32:
        array_string = 'i'
    elif data.dtype == numpy.uint32:
        array_string = 'I'
    else:
        raise NotImplementedError("ElementType " + str(data.dtype) + " not implemented.")
    a = array.array(array_string)
    a.fromlist(list(data.ravel()))
    # if is_little_endian():
    #    a.byteswap()
    a.tofile(rawfile)
    rawfile.close()


def write_mhd_file(mhdfile, data, **meta_dict):
    assert(mhdfile[-4:] == '.mhd')
    meta_dict['ObjectType'] = 'Image'
    meta_dict['BinaryData'] = 'True'
    meta_dict['BinaryDataByteOrderMSB'] = 'False'
    if data.dtype == numpy.float32:
        meta_dict['ElementType'] = 'MET_FLOAT'
    elif data.dtype == numpy.double or data.dtype == numpy.float64:
        meta_dict['ElementType'] = 'MET_DOUBLE'
    elif data.dtype == numpy.byte:
        meta_dict['ElementType'] = 'MET_CHAR'
    elif data.dtype == numpy.uint8 or data.dtype == numpy.ubyte:
        meta_dict['ElementType'] = 'MET_UCHAR'
    elif data.dtype == numpy.short or data.dtype == numpy.int16:
        meta_dict['ElementType'] = 'MET_SHORT'
    elif data.dtype == numpy.ushort or data.dtype == numpy.uint16:
        meta_dict['ElementType'] = 'MET_USHORT'
    elif data.dtype == numpy.int32:
        meta_dict['ElementType'] = 'MET_INT'
    elif data.dtype == numpy.uint32:
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
    meta_dict['ElementDataFile'] = os.path.split(mhdfile)[1].replace('.mhd',
                                                                     '.raw')

    # Tags that need conversion of list to string
    tags = ['ElementSpacing', 'Offset', 'DimSize', 'CenterOfRotation', 'TransformMatrix']
    for tag in tags:
        if tag in meta_dict.keys():
            meta_dict[tag] = ' '.join([str(i) for i in meta_dict[tag]])
    write_meta_header(mhdfile, meta_dict)

    pwd = os.path.split(mhdfile)[0]
    if pwd:
        data_file = pwd + '/' + meta_dict['ElementDataFile']
    else:
        data_file = meta_dict['ElementDataFile']

    dump_raw_data(data_file, data, dsize, element_channels=element_channels)
