import unittest

from thread_logic import COMMON_PRESETS, ThreadStandard, calculate_thread_values, parse_thread_inputs


class ThreadCalculatorTests(unittest.TestCase):
    def test_m8_values(self):
        values = calculate_thread_values(8.0, 1.25)
        self.assertAlmostEqual(values.standard_tap_drill, 6.796835, places=6)
        self.assertAlmostEqual(values.print_hole, 6.996835, places=6)
        self.assertAlmostEqual(values.print_bolt, 7.8, places=6)
        self.assertAlmostEqual(values.min_layer, 0.125, places=6)
        self.assertAlmostEqual(values.max_layer, 0.25, places=6)

    def test_m18_values(self):
        values = calculate_thread_values(18.0, 2.5)
        self.assertAlmostEqual(values.standard_tap_drill, 15.59367, places=5)
        self.assertAlmostEqual(values.print_hole, 15.89367, places=5)
        self.assertAlmostEqual(values.print_bolt, 17.65, places=6)

    def test_sae_quarter_20_values(self):
        parsed = parse_thread_inputs("SAE", 0.25, 20)
        values = calculate_thread_values(parsed.diameter, parsed.pitch)
        self.assertAlmostEqual(parsed.pitch, 1.27, places=6)
        self.assertAlmostEqual(values.standard_tap_drill * parsed.display_scale, 0.2018734, places=6)
        self.assertAlmostEqual(values.print_hole * parsed.display_scale, 0.2097474, places=6)
        self.assertAlmostEqual(values.print_bolt * parsed.display_scale, 0.2421260, places=6)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            calculate_thread_values(0, 1.0)
        with self.assertRaises(ValueError):
            parse_thread_inputs("metric", 8.0, 0)

    def test_common_presets_cover_requested_sizes(self):
        preset_names = {preset.name: preset.standard for preset in COMMON_PRESETS}
        self.assertEqual(preset_names["M5 × 0.8"], ThreadStandard.METRIC)
        self.assertEqual(preset_names["M6 × 1.0"], ThreadStandard.METRIC)
        self.assertEqual(preset_names["M8 × 1.25"], ThreadStandard.METRIC)
        self.assertEqual(preset_names["1/4-20 UNC"], ThreadStandard.SAE)
        self.assertEqual(preset_names["3/8-16 UNC"], ThreadStandard.SAE)


if __name__ == "__main__":
    unittest.main()
