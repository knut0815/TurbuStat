
from spectral_cube import SpectralCube, LazyMask
from spectral_cube.wcs_utils import drop_axis
from signal_id import Noise, RadioMask
import numpy as np
from astropy.io import fits
from astropy.convolution import convolve
from scipy import ndimage as nd


class Mask_and_Moments(object):
    """docstring for Mask_and_Moments"""
    def __init__(self, cube, noise_type='constant', clip=3):
        super(Mask_and_Moments, self).__init__()

        if isinstance(cube, SpectralCube):
            self.cube = cube
        else:
            self.cube = SpectralCube.read(cube)

        self.noise_type = noise_type
        self.clip = clip

        self.scale = Noise(self.cube).scale

    def find_noise(self, return_obj=False):

        noise = Noise(self.cube)

        self.scale = noise.scale

        if return_obj:
            return noise

        return noise.scale

    def make_mask(self, mask=None):

        if mask is None:
            rad_mask = RadioMask(self.cube)
            mask = rad_mask.to_mask()

        self.cube = self.cube.with_mask(mask)

        return self

    def make_moments(self, units=False):

        self._moment0 = self.cube.moment0()
        self._moment1 = self.cube.moment1()
        self._moment2 = self.cube.moment2()
        self._intint = self._get_int_intensity()

        if not units:
            self._moment0 = self._moment0.value
            self._moment1 = self._moment1.value
            self._moment2 = self._moment2.value
            self._intint = self._intint.value
        return self

    def make_moment_errors(self):

        self._moment0_err = self._get_moment0_err()
        self._moment1_err = self._get_moment1_err()
        self._moment2_err = self._get_moment2_err()
        self._intint_err = self._get_int_intensity_err()

        return self

    @property
    def moment0(self):
        return self._moment0

    @property
    def moment1(self):
        return self._moment1

    @property
    def moment2(self):
        return self._moment2

    @property
    def linewidth(self):
        return np.sqrt(self.moment2)

    @property
    def intint(self):
        return self._intint

    @property
    def moment0_err(self):
        return self._moment0_err

    @property
    def moment1_err(self):
        return self._moment1_err

    @property
    def moment2_err(self):
        return self._moment2_err

    @property
    def linewidth_err(self):
        return self.moment2_err / (2 * self.moment2)

    @property
    def intint_err(self):
        return self._intint_err

    def all_moments(self):
        return [self._moment0, self._moment1, self._moment2, self._intint]

    def all_moment_errs(self):
        return [self._moment0_err, self._moment1_err, self._moment2_err,
                self._intint_err]

    def to_fits(self, save_name):
        '''
        Save the property arrays as fits files.
        '''

        bunits = [self.cube.spatial_unit, self.cube.spectral_unit,
                  self.cube.spectral_unit,
                  self.cube.spatial_unit*self.cube.spectral_unit]

        comments = ["Image of the Zeroth Moment",
                    "Image of the First Moment",
                    "Image of the Second Moment",
                    "Image of the Integrated Intensity"]

        labels = ["_moment0", "_centroid", "_linewidth", "_intint"]

        for i, (arr, err) in enumerate(zip(self.all_moments(),
                                           self.all_moment_errs())):

            wcs = self.cube.wcs.copy()
            new_wcs = drop_axis(wcs, 0)

            hdr = new_wcs.to_header()
            hdr_err = new_wcs.to_header()
            hdr["BUNIT"] = bunits[i]
            hdr_err["BUNIT"] = bunits[i]
            hdr["COMMENT"] = comments[i]
            hdr_err["COMMENT"] = comments[i] + " Error."

            hdu = fits.HDUList([fits.PrimaryHDU(arr, header=hdr),
                                fits.ImageHDU(err, header=hdr_err)])

            hdu.writeto(save_name+labels[i]+".fits")

    def _get_int_intensity(self):
        '''
        Get an integrated intensity image of the cube.

        Parameters
        ----------

        '''

        noise = self.find_noise(return_obj=True)

        noise.calculate_spectral()

        good_channels = noise.spectral_norm > noise.scale

        channel_range = self.cube.spectral_axis[good_channels][[0, -1]]

        channel_size = np.abs(self.cube.spectral_axis[1] -
                              self.cube.spectral_axis[0])

        slab = self.cube.spectral_slab(*channel_range).filled_data[:]

        return np.nansum(slab, axis=0) * channel_size

    def _get_int_intensity_err(self):
        '''
        '''

        noise = self.find_noise(return_obj=True)

        noise.calculate_spectral()

        good_channels = noise.spectral_norm > noise.scale

        channel_range = self.cube.spectral_axis[good_channels][[0, -1]]

        channel_size = np.abs(self.cube.spectral_axis[1] -
                              self.cube.spectral_axis[0])

        slab = self.cube.spectral_slab(*channel_range).filled_data[:]

        return self.scale * channel_size * \
            np.sqrt(np.sum(np.isfinite(slab), axis=0))

    def _get_moment0_err(self):
        '''
        '''

        error_arr = self.scale * \
            np.sqrt(np.sum(self.cube.mask.include(), axis=0))

        return error_arr

    def _get_moment1_err(self):
        '''
        '''

        pix_cen = self.cube._pix_cen()[0]

        good_pix = np.isfinite(self.moment0) + np.isfinite(self.moment1)

        error_arr = np.zeros(self.moment1.shape)

        term1 = np.power(self.scale *
                         np.sum(pix_cen * good_pix, axis=0)[good_pix] /
                         self.moment1[good_pix], 2)

        term2 = np.power(self._get_moment0_err()[good_pix], 2)

        error_arr[good_pix] = (1 / self.moment0[good_pix]) * \
            np.sqrt(term1 + term2)

        error_arr[~good_pix] = np.NaN

        return error_arr

    def _get_moment2_err(self):
        '''
        '''

        pix_cen = self.cube._pix_cen()[0]

        data = self.cube._get_filled_data() * self.cube._pix_size()[0]

        good_pix = np.isfinite(self.moment0) + np.isfinite(self.moment1) + \
            np.isfinite(self.moment2)

        error_arr = np.zeros(self.moment2.shape)

        term11 = self.scale * \
            np.power(np.sum(pix_cen * good_pix, axis=0)[good_pix] -
                     self.moment1[good_pix], 2)

        term12 = 2 * \
            np.nansum((data * good_pix) *
                      ((pix_cen * good_pix) -
                      self.moment1), axis=0)[good_pix] * \
            self._get_moment1_err()[good_pix]

        term1 = np.power((term11 - term12) / self.moment2[good_pix], 2)

        term2 = np.power(self._get_moment0_err()[good_pix], 2)

        error_arr[good_pix] = (1 / self.moment0[good_pix]) * \
            np.sqrt(term1 + term2)

        error_arr[~good_pix] = np.NaN

        return error_arr


def moment_masking(cube, kernel_size, clip=5, dilations=1):
    '''
    '''

    smooth_data = convolve(cube.filled_data[:], gauss_kern(kernel_size))

    fake_mask = LazyMask(np.isfinite, cube=cube)

    smooth_cube = SpectralCube(data=smooth_data, wcs=cube.wcs, mask=fake_mask)

    smooth_scale = Noise(smooth_cube).scale

    mask = (smooth_cube > (clip * smooth_scale)).include()

    # Now dilate the mask once

    dilate_struct = nd.generate_binary_structure(3, 3)
    mask = nd.binary_dilation(mask, structure=dilate_struct,
                              iterations=dilations)

    return mask


def gauss_kern(size, ysize=None, zsize=None):
    """ Returns a normalized 3D gauss kernel array for convolutions """
    size = int(size)
    if not ysize:
        ysize = size
    else:
        ysize = int(ysize)
    if not zsize:
        zsize = size
    else:
        zsize = int(zsize)

    x, y, z = np.mgrid[-size:size + 1, -ysize:ysize + 1, -zsize:zsize + 1]
    g = np.exp(-(x ** 2 / float(size) + y **
                 2 / float(ysize) + z ** 2 / float(zsize)))
    return g / g.sum()
