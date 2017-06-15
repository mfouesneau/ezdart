"""
EZDART -- A python package that allows you to download MESA isochrones directly
from the DARTMOUTH directly website

based on EZPADOVA

:version: 1.0
:author: MF
"""
from __future__ import print_function, unicode_literals, division

import sys
import os
import inspect

if sys.version_info[0] > 2:
    py3k = True
    from urllib import request
    from urllib.request import urlopen
else:
    py3k = False
    from urllib2 import urlopen

import zlib
import re
import json
from simpletable import SimpleTable as Table


localpath = '/'.join(os.path.abspath(inspect.getfile(inspect.currentframe())).split('/')[:-1])

with open(localpath + '/dart.json') as f:
    _cfg = json.load(f)


# Help messages
# -------------

def file_type(filename, stream=False):
    """ Detect potential compressed file
    Returns the gz, bz2 or zip if a compression is detected, else None.
    """
    magic_dict = {"\x1f\x8b\x08": "gz",
                  "\x42\x5a\x68": "bz2",
                  "\x50\x4b\x03\x04": "zip",
                  b"\x50\x4b\x03\x04": "zip",
                  "PK\x03\x04": "zip",
                  b"PK\x03\x04": "zip",
                  }

    max_len = max(len(x) for x in magic_dict)
    if not stream:
        with open(filename) as f:
            file_start = f.read(max_len)
        for magic, filetype in magic_dict.items():
            if file_start.startswith(magic):
                return filetype
    else:
        for magic, filetype in magic_dict.items():
            if filename[:len(magic)] == magic:
                return filetype

    return None


# Build up URL request
# --------------------

def _get_url_args(**opts):
    """ Generates the query arguments given the selected options

    Parameters
    ----------
    opts: dict
        any field value

    Returns
    -------
    q: str
        string of arguments (joined by `&` char)
    """
    _opts = _cfg['defaults']

    for k, v in opts.items():
        if type(v) != int:
            try:
                values = _cfg['{0:s}_options'.format(k)]
                for e, value in enumerate(values, 1):
                    if k == value:
                        _opts[k] = e
                        break
            except KeyError:
                _opts[k] = v
        else:
            _opts[k] = v

    # check None = ""
    q = []
    keys = _cfg["query_options"]

    for k in keys:
        val = _opts.get(k, "")
        if val is None:
            val = ""
        q.append("{key}={val}".format(key=k, val=val))

    return '&'.join(q)


def _extract_zip(zip_bytes):
    """ Extract the content of a zip file

    Parameters
    ----------
    zip_bytes: bytes
        string that contains the binary code

    Returns
    -------
    content:str
        ascii string contained in the zip code.
    """
    import io
    import zipfile
    fp = zipfile.ZipFile(io.BytesIO(zip_bytes))
    data = {name: fp.read(name) for name in fp.namelist()}
    if len(data) > 1:
        return data
    else:
        return data[list(data.keys())[0]]


def _query_website(q):
    """ Run the query on the website

    Parameters
    ----------
    q: str
        string of arguments (joined by `&` char)

    Returns
    -------
    r: str or bytes
        unzipped content of the query
    """

    url = _cfg["request_url"]
    print('Interrogating {0}...'.format(url))

    print('Request...', end='')
    if py3k:
        c = urlopen(url + '?' + q).read().decode('utf8')
        print('done.')
        print("Reading content...", end='')
    else:
        c = urlopen(url, q).read()
    print('done.')

    if "sorry" in c.lower():
        print(url + '?' + q)
        print(c)
        raise RuntimeError("Something went wrong")

    try:
        fname = re.compile('<a href=".*iso">').findall(c)[0][9:-2]
    except Exception as e:
        print(e)
        raise RuntimeError("Something went wrong")

    furl = _cfg['download_url'] + '/' + fname

    print('Downloading data...{0}...'.format(furl), end='')
    if py3k:
        req = request.Request(furl)
        bf = urlopen(req)
    else:
        bf = urlopen(furl)
    r = bf.read()
    print("done.")

    typ = file_type(r, stream=True)
    # force format
    if (typ is None) & ('zip' in fname):
        typ = 'zip'
    if typ is not None:
        print(r[:100], type(r), bytes(r[:10]))
        print("decompressing archive (type={0})...".format(typ), end='')
        if 'zip' in typ:
            r = _extract_zip(bytes(r))
        else:
            r = zlib.decompress(bytes(r), 15 + 32)
        print("done.")

    return r


def _read_dart_iso_filecontent(data):

    """
    Reads in the isochrone file.

    Parameters
    ----------
    data: str or bytes
        content from the unzipped website query

    Returns
    -------
    t: Table
        table of the isochrones
    """
    import numpy as np

    try:
        f = data.decode('utf8').split('\n')
    except:
        f = data.split('\n')

    num_ages = int(re.compile('.*AGES=.* ').findall(f[0])[0].split('=')[-1])
    hdr = dict(zip(f[2][1:].split(), [float(k) for k in f[3][1:].split()]))

    # read one block for each isochrone
    iso_set = []
    counter = 0
    data = f[7:]

    ages = []

    # isochrone format
    for i_age in range(num_ages):

        # grab info for each isochrone
        _d = data[counter]
        age, num_eeps = _d[1:][len('AGE='):].split()
        num_eeps = int(num_eeps[len('EEPS='):])
        hdr_list = data[counter + 1][1:].split()
        num_cols = len(hdr_list)
        if not py3k:
            # correcting for recfunctions not up to date for unicode dtypes
            hdr_list = [str(k) for k in hdr_list]
        formats = tuple([np.int32] + [np.float64 for i in range(num_cols - 1)])
        iso = np.zeros((num_eeps), {'names':tuple(hdr_list),'formats':tuple(formats)})

        # read through EEPs for each isochrone
        for eep in range(num_eeps):
            iso_chunk = data[2 + counter + eep]
            iso[eep] = tuple(iso_chunk.split())

        iso_set.append(iso)
        ages.extend([float(age)] * num_eeps)

        counter += 3 + num_eeps + 1

    _data = np.lib.recfunctions.stack_arrays(iso_set, usemask=False)

    t = Table(_data, header=hdr)
    t.add_column('age', np.array(ages), dtype=np.float64)

    # make some aliases
    aliases = (('logL', 'LogL/Lo'),
               ('logT', 'LogTeff'),
               ('mass', 'M/Mo'),
               ('logg', 'LogG'))

    for a, b in aliases:
        t.set_alias(a, b)
    t.header['NAME'] = 'Dartmouth isochrones'

    return t


# Convenient Functions
# --------------------

def simple_options(**kwargs):
    opts = _cfg['defaults']
    opts.update(kwargs)
    return opts


def get_standard_isochrone(ret_table=True, **kwargs):
    """ get the default isochrone set at a given time and [Fe/H]

    DART standard age grid

    Parameters
    ----------

    ret_table: bool
        if set, return a eztable.Table object of the data

    **kwargs: other options

    Returns
    -------
    r: Table or str
        if ret_table is set, return a eztable.Table object of the data
        else return the string content of the data
    """
    # Default ages
    import numpy as np
    ages = '+'.join(map(str, np.arange(1, 15.1, 0.25).tolist()))
    opts = simple_options(age=ages, **kwargs)

    d = _get_url_args(**opts)

    r = _query_website(d)
    if ret_table is True:
        return _read_dart_iso_filecontent(r)
    else:
        return r


def get_one_isochrone(age, FeH, ret_table=True, **kwargs):
    """ get one isochrone at a given time and [Fe/H]

    Parameters
    ----------

    age: float
        age of the isochrone (in Gyr)

    metal: float
        metalicity of the isochrone

    ret_table: bool
        if set, return a eztable.Table object of the data

    **kwargs: other options

    Returns
    -------
    r: Table or str
        if ret_table is set, return a eztable.Table object of the data
        else return the string content of the data
    """
    opts = simple_options(age=age, feh=FeH, **kwargs)

    d = _get_url_args(**opts)

    r = _query_website(d)
    if ret_table is True:
        return _read_dart_iso_filecontent(r)
    else:
        return r


def get_t_isochrones(t0, t1, dt, ret_table=True, **kwargs):
    """ get a sequence of isochrones at constant Z

    Parameters
    ----------
    t0: float
        minimal value of (t/Gyr)

    t1: float
        maximal value of (t/Gyr)

    dt: float
        step in (t/Gyr) for the sequence

    ret_table: bool
        if set, return a eztable.Table object of the data

    Returns
    -------
    r: Table or str
        if ret_table is set, return a eztable.Table object of the data
        else return the string content of the data
    """
    opts = simple_options(**kwargs)

    d = _get_url_args(**opts)

    r = _query_website(d)
    if ret_table is True:
        return _read_dart_iso_filecontent(r)
    else:
        return r
