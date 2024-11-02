import unittest
import numpy as np
from scipy.io import wavfile
from app import apply_equalizer

# Giả sử apply_equalizer đã được import từ file module
# from my_module import apply_equalizer

class TestEqualizer(unittest.TestCase):

    def setUp(self):
        # Thiết lập tín hiệu mẫu và tần số lấy mẫu
        self.rate = 44100  # Tần số mẫu
        self.duration = 1  # 1 giây
        self.data = np.sin(2 * np.pi * 440 * np.linspace(0, self.duration, self.rate * self.duration)) * 32767
        self.data = self.data.astype(np.int16)  # Chuyển đổi sang định dạng int16

    def test_equalizer_no_gain(self):
        # Kiểm tra khi tất cả các gain đều là 0 (không có thay đổi)
        gains = [0, 0, 0, 0, 0, 0, 0]
        filtered_data = apply_equalizer(self.data, self.rate, gains)
        # Kết quả đầu ra không thay đổi so với đầu vào
        np.testing.assert_array_almost_equal(self.data, filtered_data, decimal=2)

    def test_equalizer_positive_gain(self):
        # Kiểm tra khi tất cả các gain là dương (tăng cường độ âm lượng)
        gains = [2, 2, 2, 2, 2, 2, 2]
        filtered_data = apply_equalizer(self.data, self.rate, gains)
        # Đảm bảo đầu ra có giá trị khác so với đầu vào (do gain dương)
        self.assertFalse(np.array_equal(self.data, filtered_data))

    def test_equalizer_negative_gain(self):
        # Kiểm tra khi tất cả các gain là âm (giảm cường độ âm lượng)
        gains = [-2, -2, -2, -2, -2, -2, -2]
        filtered_data = apply_equalizer(self.data, self.rate, gains)
        # Đảm bảo đầu ra có giá trị khác so với đầu vào (do gain âm)
        self.assertFalse(np.array_equal(self.data, filtered_data))

    def test_output_length_matches_input(self):
        # Đảm bảo độ dài tín hiệu đầu ra khớp với tín hiệu đầu vào
        gains = [1, 1, 1, 1, 1, 1, 1]
        filtered_data = apply_equalizer(self.data, self.rate, gains)
        self.assertEqual(len(filtered_data), len(self.data))

    def test_output_clipping(self):
        # Kiểm tra không có clipping trong tín hiệu đầu ra
        gains = [5, 5, 5, 5, 5, 5, 5]
        filtered_data = apply_equalizer(self.data, self.rate, gains)
        # Đảm bảo tín hiệu đầu ra nằm trong khoảng int16
        self.assertTrue(np.all(filtered_data <= 32767) and np.all(filtered_data >= -32768))

if __name__ == "__main__":
    unittest.main()
