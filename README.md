EZDART -- A python package that allows you to download DARTMOUTH isochrones directly from their website
=======================================================================================================


This small package provides a direct interface to the DARTMOUTH isochrone
webpage (http://stellar.dartmouth.edu/models/isolf_new.html)
It compiles the URL needed to query the website and retrives the data into a
python variable.

This package has been tested on python 2.7 and python 3.

:version: 1
:author: MF

(this package is similar to EzPadova https://github.com/mfouesneau/ezpadova & EzMIST:  https://github.com/mfouesneau/ezmist)


EXAMPLE USAGE
-------------

* Basic example of downloading a sequence of isochrones, plotting, saving
```python 
>>> r = ezdart.get_t_isochrones(1, 15.0, 0.05, feh=0.0)
>>> import pylab as plt
>>> plt.scatter(r['logT'], r['logL'], c=r['logA'], edgecolor='None')
>>> plt.show()
>>> r.write('myiso.fits')
```

Note: 

* isochrone metallicities are defined in terms of [Fe/H] (not Z) 
* isochrone ages are (linear) in Gyr from 1 to 15.

* getting only one isochrone
```python 
>>> r = ezmist.get_one_isochrones(5, -1)
```
