import numpy as np
import math

from . import Tomogram

class ProcessableTomogram(Tomogram):

    def __init__(self, session, tomogram, rendering_options=None, average_when_slab_change=False, num_averaging_slabs=0):
        self.original_data = tomogram.data
        from chimerax.map_data import ArrayGridData
        array_data = ArrayGridData(tomogram.matrix().copy(), name='Processable ' + tomogram.data.name)

        Tomogram.__init__(self, session, array_data, rendering_options)

        self.average_when_slab_change = False

        self._num_averaging_slabs = num_averaging_slabs
        self.processed_rows = [False]*array_data.size[2]

    @property
    def num_averaging_slabs(self):
        return self._num_averaging_slabs

    @num_averaging_slabs.setter
    def num_averaging_slabs(self, value):
        if value > 0:
            self.processed_rows = [False]*self.original_data.size[2]
            self._num_averaging_slabs = int(value)

    def _set_integer_slice(self, slice=None):
        if slice is None:
            slice = self.integer_slab_position
        slice = int(slice)

        if self.average_when_slab_change:
            # Calculate the average value with the original tomo if it hasn't already been calculated
            if not self.processed_rows[slice]:
                num_surrounding_slices = 10
                for surrounding_slice in range(max(slice-num_surrounding_slices, 0), min(slice+num_surrounding_slices+1, self.size[2])):
                    if not self.processed_rows[surrounding_slice]:
                        start_z = max(surrounding_slice-self.num_averaging_slabs, 0)
                        end_z = min(surrounding_slice+self.num_averaging_slabs, self.size[2]-1)
                        num_slabs = surrounding_slice-start_z + 1 + end_z-surrounding_slice
                        relevant_matrix = self.original_data.matrix(ijk_origin=(0,0,start_z), ijk_size=(self.size[0], self.size[1], num_slabs))

                        current_slice_average = np.mean(relevant_matrix, axis=0)
                        self.data.array[surrounding_slice] = current_slice_average
                        self.processed_rows[surrounding_slice] = True

                # Update the graphics... would be cool to do without the stupid private function VERY SLOW
                if self._image and not self._image.deleted:
                    self._image._remove_planes()

        offset = slice * self.pixelsize[0] + self.min_offset
        self.slab_position = offset

    def filter_current_slab(self, slab, lp, hp, lpd=None, hpd=None, thresh=0.001):
        shape = self.size  # (x,y,z)
        slab_data = self.original_data.matrix(ijk_origin=(0, 0, slab), ijk_size=(shape[0], shape[1], 1))

        import numpy.fft as fft
        import time

        if lpd is None:
            lpd = lp / 4
        if hpd is None:
            hpd = hp / 4

        t0 = time.time()

        # Tz, Ty, Tx = np.asarray(self.size) * self.pixelsize  # ??? is this in Ångström?
        Ny, Nx = shape[1], shape[0]
        # fy, fx = fft.fftfreq(Ny), fft.rfftfreq(Nx)  # rfftn only does rfft on last axis, for the others it does normal fft
        yy, xx = np.meshgrid(fft.fftfreq(Ny), fft.rfftfreq(Nx), indexing='ij')
        # yy, xx = np.meshgrid(np.arange(shape[1]), np.arange(shape[0]), indexing='ij')
        # xx, yy = xx - math.floor(shape[0]/2), yy - math.floor(shape[1]/2)  # centering
        r = np.sqrt(np.square(xx) + np.square(yy))

        t1 = time.time()

        if lp == 0 and lpd == 0:  # skip low pass
            lpv = np.ones(r.shape)
        elif lp > 0 and lpd == 0:  # box filter (not smart but who said you have to be smart)
            lpv = np.array(r < lp, dtype=np.float32)
        elif lp == 0 and lpd > 0:  # gaussian from the start
            lpv = np.exp(-np.square(np.divide(r - (lp - lpd * 0.5), lpd * 0.5)))
        else:  # normal box + gaussian decay
            lpv = np.array(r < lp, dtype=np.float32)
            sel = (r > (lp - lpd * 0.5))
            lpv[sel] = np.exp(-np.square(np.divide(r[sel] - (lp - lpd * 0.5), lpd * 0.5)))
        lpv[lpv < thresh] = 0

        if hp == 0 and hpd == 0:  # skip high pass
            hpv = np.zeros(r.shape)
        elif hp > 0 and hpd == 0:  # box filter
            hpv = np.array(r < hp, dtype=np.float32)
        elif hp == 0 and hpd > 0:  # gaussian from the start
            hpv = np.exp(-np.square(np.divide(r - (hp - hpd * 0.5), hpd * 0.5)))
        else:  # box + gaussian decay
            hpv = np.array(r < hp, dtype=np.float32)
            sel = (r > (hp - hpd * 0.5))
            hpv[sel] = np.exp(-np.square(np.divide(r[sel] - (hp - hpd * 0.5), hpd * 0.5)))
        hpv[hpv < thresh] = 0
        hpv = 1 - hpv

        filter = np.multiply(lpv, hpv)

        t2 = time.time()

        # fft_data = fft.fft2(slab_data)  # Wierd to use fft2 and not fftn but seems to work and is much quicker
        fft_data = fft.rfftn(slab_data)
        # filtered_data = np.array(fft.ifft2(np.multiply(fft_data, fft.fftshift(filter))), dtype=np.float32)
        filtered_data = np.array(fft.irfft2(np.multiply(fft_data, fft.fftshift(filter))), dtype=np.float32)
        t3 = time.time()
        self.data.array[slab] = filtered_data
        if self._image and not self._image.deleted:
            self._image._remove_planes()

        t4 = time.time()

        print(t1 - t0, t2 - t1, t3 - t2, t4 - t3, t4 - t0)
        return filter





