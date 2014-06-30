
'''
Test functions for Tsallis
'''

import numpy as np

from ..statistics import Tsallis, Tsallis_Distance
from ._testing_data import dataset1, dataset2, computed_data, computed_distances

class testTsallis():

    def __init__(self):
        self.dataset1 = dataset1
        self.dataset2 = dataset2
        self.computed_data = computed_data
        self.computed_distances = computed_distances
        self.tester = None

    def test_Tsallis_method(self):
        self.tester = Tsallis(dataset1["integrated_intensity"][0])
        self.tester.run()
        assert np.allclose(self.tester.tsallis_fits, self.computed_data['tsallis_val'])

    def test_Tsallis_distance(self):
        self.tester_dist = Tsallis_Distance(dataset1["integrated_intensity"][0], dataset2["integrated_intensity"][0], fiducial_model = self.tester).distance_metric().distance
        assert np.allclose(self.tester_dist, self.computed_distances['tsallis_distance'])
