import numpy as np

from . import Tomogram

class ProcessableTomogram(Tomogram):

    def __init__(self, session, tomogram, rendering_options=None, num_averaging_slabs=0):
        self.original_data = tomogram.data
        from chimerax.map_data import ArrayGridData
        array_data = ArrayGridData(tomogram.matrix().copy(), name='Processable ' + tomogram.data.name)

        Tomogram.__init__(self, session, array_data, rendering_options)

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





