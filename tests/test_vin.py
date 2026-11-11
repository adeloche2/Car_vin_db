import unittest
from gvidb.vin import normalize, validate, check_digit, positions, year_candidates

class VINTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize("1hg-cm82633a004352"),"1HGCM82633A004352")
    def test_known_check_digit(self):
        self.assertEqual(check_digit("1HGCM82633A004352")["status"],"pass")
    def test_modified_check_digit(self):
        self.assertEqual(check_digit("1HGCM82643A004352")["status"],"mismatch")
    def test_forbidden_letter(self):
        self.assertFalse(validate("1HGCM82633A00435I")["valid_shape"])
    def test_positions(self):
        result=positions("1HGCM82633A004352")
        self.assertEqual(result["wmi"],"1HG")
        self.assertEqual(result["year_code"],"3")
        self.assertEqual(result["serial"],"004352")
    def test_year_candidates(self):
        self.assertEqual(year_candidates("A"),[1980,2000,2020])

if __name__ == "__main__":
    unittest.main()
