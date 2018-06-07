import unittest
from tempfile import NamedTemporaryFile
from os import remove
from mailer import *


class TestScore(unittest.TestCase):

    def test_initialize_with_str(self):
        test_values = "-1.0 -1.5 0.0 0.1 9.9 10.1 13.0"
        for v in test_values.split():
            score = Score(v)
            self.assertEqual(str(score), v)

    def test_initialize_with_float(self):
        for i in range(-20, 20):
            val = i/10.0
            score = Score(val)
            self.assertAlmostEqual(val, float(score), 1)

    def test_gt(self):
        self.assertTrue(Score(1.1) > Score(1.0))

    def test_le(self):
        self.assertTrue(Score(1.0) < Score(1.1))

    def test_le_and_equal(self):
        for i in range(-22, 22):
            x = i/10
            y = (i+1)/10 - 0.1
            self.assertTrue(Score(x) <= Score(y))
            self.assertTrue(Score(x) == Score(y))

    def test_ranges(self):
        for rn in Score.grading:
            step = (rn[1]-rn[0])/10
            _score = rn[0]+step
            score = Score(_score)
            while score <= Score(rn[1]):
                result = score.get_grade()
                self.assertEqual(result[0], rn[2])
                self.assertEqual(result[1], rn[3])
                _score += step
                score = Score(_score)

class TestResults(unittest.TestCase):

    def setUp(self):
        self.data = []
        with open('wyniki.csv') as fp:
            line = fp.readline()
            while line:
                self.data.append(line.strip())
                line = fp.readline()

    def test_length(self):
        results = get_results('wyniki.csv')
        self.assertEqual(len(self.data), len(results))

    def test_content(self):
        results = get_results('wyniki.csv')
        for k,v in results.items():
            if v > 0.0:
                line = "%s;%.1f" % (k,v)
                self.assertTrue(line in self.data)
            else:
                line1 = "%s;0.0" % k
                line2 = "%s;" % k
                self.assertTrue(line1 in self.data or \
                                line2 in self.data)


class TestComposeBody(unittest.TestCase):

    def setUp(self):
        body = "-@SCORE@-@GRADENUM@-@GRADETXT@-@EPILOGUE@-"
        with NamedTemporaryFile(mode='w', delete=False) as fp:
            fp.write(body)
            self.filename = fp.name

    def tearDown(self):
        remove(self.filename)

    def test_compose(self):
        for i, grad in enumerate(Score.grading):
            score = Score((grad[0]+grad[1])/2)
            num = grad[2]
            txt = grad[3]
            rendered = compose_body(self.filename, score)
            if i == 0:
                epilogue = "Życzę powodzenia na poprawie,"
            else:
                epilogue = "Gratuluję,"
            expected = "-{}-{}-{}-{}-".format(str(score), num, txt, epilogue)
            self.assertEqual(rendered, expected)


if __name__ == '__main__':
    unittest.main()
