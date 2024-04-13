import numpy as np
import math

from . import Tomogram


class ProcessableTomogram(Tomogram):
    def __init__(self, session, tomogram, region=None, rendering_options=None, average_when_slab_change=False,
                 filter_when_slab_change=False, num_averaging_slabs=0):
        self.original_data = tomogram.data
        from chimerax.map_data import ArrayGridData
        array_data = ArrayGridData(tomogram.matrix().copy(), name='Processable ' + tomogram.data.name)

        Tomogram.__init__(self, session, array_data, region=region, rendering_options=rendering_options)

        self._filter_when_slab_change = filter_when_slab_change
        self.lp = 0
        self.hp = 0
        self.lpd = None
        self.hpd = None
        self.unit = 'pixels'
        self.method = 'gaussian'
        self.thresh = 0.001

        self._average_when_slab_change = average_when_slab_change
        self._num_averaging_slabs = num_averaging_slabs
        self.processed_rows = [False]*array_data.size[2]

    @property
    def filter_when_slab_change(self):
        return self._filter_when_slab_change

    @filter_when_slab_change.setter
    def filter_when_slab_change(self, value):
        if value and self.average_when_slab_change:
            self.average_when_slab_change = False
            self.processed_rows = [False]*self.data.size[2]
        self._filter_when_slab_change = value

    @property
    def average_when_slab_change(self):
        return self._average_when_slab_change

    @average_when_slab_change.setter
    def average_when_slab_change(self, value):
        if value and self.filter_when_slab_change:
            self.filter_when_slab_change = False
            self.processed_rows = [False]*self.data.size[2]
        self._average_when_slab_change = value

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

        if self.average_when_slab_change or self.filter_when_slab_change:
            # Calculate the average value with the original tomo OR filter slices if it hasn't already been done
            if not self.processed_rows[slice]:
                num_surrounding_slices = 10
                for surrounding_slice in range(max(slice-num_surrounding_slices, 0), min(slice+num_surrounding_slices+1, self.size[2])):
                    if not self.processed_rows[surrounding_slice]:
                        if self.average_when_slab_change:
                            start_z = max(surrounding_slice-self.num_averaging_slabs, 0)
                            end_z = min(surrounding_slice+self.num_averaging_slabs, self.size[2]-1)
                            num_slabs = surrounding_slice-start_z + 1 + end_z-surrounding_slice
                            relevant_matrix = self.original_data.matrix(ijk_origin=(0,0,start_z), ijk_size=(self.size[0], self.size[1], num_slabs))

                            computed_row = np.mean(relevant_matrix, axis=0)
                            self.processed_rows[surrounding_slice] = True
                        elif self.filter_when_slab_change:
                            computed_row = self.filter_slab(surrounding_slice)

                        self.data.array[surrounding_slice] = computed_row
                        self.processed_rows[surrounding_slice] = True

                # Update the graphics... would be cool to do without the stupid private function VERY SLOW
                if self._image and not self._image.deleted:
                    self._image._remove_planes()

        offset = slice * self.pixelsize[0] + self.min_offset
        self.slab_position = offset

    def filter_slab(self, slab):
        import numpy.fft as fft

        shape = self.size  # (x,y,z)
        slab_data = self.original_data.matrix(ijk_origin=(0, 0, slab), ijk_size=(shape[0], shape[1], 1))

        if self.lpd is None:
            lpd = self.lp / 4
        else:
            lpd = self.lpd
        if self.hpd is None:
            hpd = self.hp / 4
        else:
            hpd = self.hpd

        if self.unit == 'pixels':
            Ny, Nx = shape[1], shape[0] // 2 + 1
            yy, xx = np.meshgrid(np.arange(Ny), np.arange(Nx), indexing='ij')
            xx, yy = xx - math.floor(Nx / 2), yy - math.floor(Ny / 2)  # centering
        elif self.unit == 'hz':
            Tz, Ty, Tx = np.asarray(self.size) * self.pixelsize
            Ny, Nx = shape[1], shape[0]
            fy, fx = fft.fftfreq(Ny), fft.rfftfreq(Nx)  # rfftn only does rfft on last axis, for the others it does normal fft
            yy, xx = np.meshgrid(fy, fx, indexing='ij')
            xx, yy = xx - xx[0].mean(), fft.fftshift(yy)  # centering
        else:
            raise NotImplementedError('Only "pixels" and "hx" implemented as units.')

        r = np.sqrt(np.square(xx) + np.square(yy))

        lpv = create_filter(True, r, self.lp, lpd, self.method, self.thresh)
        hpv = create_filter(False, r, self.hp, hpd, self.method, self.thresh)

        filter = np.multiply(lpv, hpv)

        fft_data = fft.rfft2(slab_data)
        filtered_data = np.array(fft.irfft2(np.multiply(fft_data, fft.fftshift(filter))), dtype=np.float32)
        return filtered_data

    def reset_to_normal(self):
        self.data.array = self.original_data.matrix().copy()
        self.processed_rows = [False]*self.data.size[2]
        if self._image and not self._image.deleted:
            self._image._remove_planes()

    def take_snapshot(self, session, flags):
        data = Tomogram.take_snapshot(self, session, flags)
        return data

    @classmethod
    def restore_snapshot(cls, session, data):
        tomo = super().restore_snapshot(session, data)
        return tomo


def create_filter(is_lp, r, pass_freq, decay, method='gaussian', thresh=0.001):
    if pass_freq == 0 and decay == 0:  # skip low pass
        if is_lp:
            filt = np.ones(r.shape)
        else:
            filt = np.zeros(r.shape)
    elif pass_freq > 0 and decay == 0:  # box filter (not smart but who said you have to be smart)
        filt = np.array(r < pass_freq, dtype=np.float32)
    else:
        if method == 'gaussian':
            if pass_freq == 0 and decay > 0:  # gaussian from the start
                filt = np.exp(-np.square(np.divide(r, decay * 0.5)))
            else:  # normal box + gaussian decay
                filt = np.array(r < pass_freq, dtype=np.float32)
                sel = (r > (pass_freq - decay * 0.5))
                filt[sel] = np.exp(-np.square(np.divide(r[sel] - (pass_freq - decay * 0.5), decay * 0.5)))
            filt[filt < thresh] = 0
        else:
            if pass_freq == 0 and decay > 0:  # raised cosine from the start
                filt = np.array(r < decay, dtype=np.float32)
                sel = (r <= decay)
                filt[sel] = 0.5 + 0.5*np.cos(np.divide(np.pi * r[sel], decay))
            else:  # normal box + raised cosine
                filt = np.array(r < pass_freq, dtype=np.float32)
                sel = (r < (pass_freq + decay * 0.5)) & (r > (pass_freq - decay * 0.5))
                filt[sel] = 0.5 + 0.5*np.cos(np.divide(np.pi * (r[sel] - (pass_freq - decay * 0.5)), decay))
    if not is_lp:
        filt = 1 - filt
    return filt




