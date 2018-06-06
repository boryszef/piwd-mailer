import unittest
import run

class TestGrading(unittest.TestCase):

    def test_ranges(self):
        for rn in run.grading:
            step = (rn[1]-rn[0])/10
            score = rn[0]+step
            while score <= rn[1]:
                result = run.get_grade(score)
                self.assertEqual(result[0], rn[2])
                self.assertEqual(result[1], rn[3])
                score += step

class TestResults(unittest.TestCase):

    def setUp(self):
        self.data = []
        with open('wyniki.csv') as fp:
            line = fp.readline()
            while line:
                self.data.append(line.strip())
                line = fp.readline()

    def test_length(self):
        results = run.get_results('wyniki.csv')
        self.assertEqual(len(self.data), len(results))

    def test_content(self):
        results = run.get_results('wyniki.csv')
        for k,v in results.items():
            if v > 0.0:
                line = "%s;%.1f" % (k,v)
                self.assertTrue(line in self.data)
            else:
                line1 = "%s;0.0" % k
                line2 = "%s;" % k
                self.assertTrue(line1 in self.data or \
                                line2 in self.data)

if __name__ == '__main__':
    unittest.main()
