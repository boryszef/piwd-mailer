import unittest
import re
from tempfile import NamedTemporaryFile
from os import remove
from sys import argv
from mailer import Score, Message, Sender, compose_body, get_results


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


class TestMessage(unittest.TestCase):

    def setUp(self):
        self.fromaddr = "me@example.com"
        self.toaddr = "you@example.net"
        self.subject = "Blah blah"
        self.bodyplain = "Hello,\nBye"
        self.bodyhtml = """<html>
        <body>
        <p>Hello,</p>
        <p>Bye <img src="image.jpg" /></p>
        </body>
        </html>"""

    def test_from(self):
        msg = Message(self.fromaddr, self.toaddr, self.subject,
                      self.bodyplain)
        txt = msg.as_string()
        result = re.search("^From: (.*)$", txt, re.M)
        self.assertTrue(result)
        self.assertEqual(result.group(1), self.fromaddr)

    def test_single_to(self):
        msg = Message(self.fromaddr, self.toaddr, self.subject,
                      self.bodyplain)
        txt = msg.as_string()
        result = re.search("^To: (.*)$", txt, re.M)
        self.assertTrue(result)
        self.assertEqual(result.group(1), self.toaddr)

    def test_multiple_to(self):
        to = ['a@b.com', 'b@c.com', 'd@e.com']
        msg = Message(self.fromaddr, to, self.subject,
                      self.bodyplain)
        txt = msg.as_string()
        result = re.search("^To: (.*)$", txt, re.M)
        self.assertTrue(result)
        self.assertEqual(result.group(1), ", ".join(to))

    def test_subject(self):
        msg = Message(self.fromaddr, self.toaddr, self.subject,
                      self.bodyplain)
        txt = msg.as_string()
        result = re.search("^Subject: (.*)$".format(self.subject), txt, re.M)
        self.assertTrue(result)
        self.assertEqual(result.group(1), self.subject)

    def test_no_body(self):
        with self.assertRaises(RuntimeError):
            Message(self.fromaddr, self.toaddr, self.subject)

    def test_plain(self):
        msg = Message(self.fromaddr, self.toaddr, self.subject,
                      self.bodyplain)
        txt = msg.as_string()
        result = re.search("^Content-Type: text/plain;", txt, re.M)
        self.assertTrue(result)

    def test_html(self):
        msg = Message(self.fromaddr, self.toaddr, self.subject,
                      bodyhtml=self.bodyhtml)
        txt = msg.as_string()
        result = re.search("^Content-Type: text/html;", txt, re.M)
        self.assertTrue(result)

    def test_plain_and_html(self):
        msg = Message(self.fromaddr, self.toaddr, self.subject,
                      self.bodyplain, self.bodyhtml)
        txt = msg.as_string()
        result = re.search("^Content-Type: multipart/alternative;", txt, re.M)
        self.assertTrue(result)

    def test_attach_image(self):
        msg = Message(self.fromaddr, self.toaddr, self.subject,
                      self.bodyplain, self.bodyhtml, ['image.jpg'])
        txt = msg.as_string()
        result = re.search("^Content-Type: image/jpeg", txt, re.M)
        self.assertTrue(result)
        result = re.search("^Content-ID: <image\d+>", txt, re.M)
        self.assertTrue(result)

    def test_attach_script(self):
        msg = Message(self.fromaddr, self.toaddr, self.subject,
                      self.bodyplain, self.bodyhtml, [argv[0]])
        txt = msg.as_string()
        result = re.search("^Content-Type: text/x-python", txt, re.M)
        self.assertTrue(result)

    def test_two_attachments(self):
        msg = Message(self.fromaddr, self.toaddr, self.subject,
                      self.bodyplain, self.bodyhtml, ['image.jpg', argv[0]])
        txt = msg.as_string()
        print(txt)
        pattern = re.compile("^Content-Disposition: attachment;")
        count = 0
        for match in pattern.finditer(txt, re.M):
            count += 1
        self.assertEqual(count, 2)


if __name__ == '__main__':
    unittest.main()
