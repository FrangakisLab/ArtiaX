import numpy as np

from . import Tomogram

class ProcessableTomogram(Tomogram):

    def __init__(self, session, array_data, rendering_options=None, num_averaging_slabs=0):
        Tomogram.__init__(self, session, array_data, rendering_options)

        self.num_averaging_slabs = num_averaging_slabs
        self.real_value_at_slab_pos = self.data.array[self.integer_slab_position].copy()

    def _set_integer_slice(self, slice=None):
        if slice is None:
            slice = self.integer_slab_position
        slice = int(slice)

        self.data.array[self.integer_slab_position] = self.real_value_at_slab_pos

        # start_z = max(offset-self.num_averaging_slabs, 0)
        # num_slabs = min(offset + 1 + self.num_averaging_slabs, self.num_averaging_slabs * 2 + 1)
        # relevant_matrix = self.data.matrix(ijk_origin=(0,0,start_z), ijk_size=(self.size[0], self.size[1], num_slabs))
        relevant_matrix = self.data.array[max(slice-self.num_averaging_slabs, 0):min(slice+self.num_averaging_slabs+1, self.size[2])]

        current_slice_average = np.mean(relevant_matrix, axis=0)
        self.real_value_at_slab_pos = self.data.array[self.integer_slab_position].copy()
        #self.data.array[self.integer_slab_position-1:self.integer_slab_position+2] = [current_slice_average]*3
        self.data.array[self.integer_slab_position] = current_slice_average

        offset = slice * self.pixelsize[0] + self.min_offset
        self.slab_position = offset



