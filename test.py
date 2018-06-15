import unittest
import re
from tempfile import NamedTemporaryFile
from os import remove
from sys import argv
from random import randint
from base64 import b64decode
from mailer import Score, Text, Message, Sender
from mailer import compose_body, get_results


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

        self.ncolumns = 4
        self.nrecords = 10
        self.header = [ 'column {}'.format(i) for i in range(self.ncolumns) ]
        self.data = []
        for i in range(self.nrecords):
            row = [i]
            row.extend([ randint(0, 100) for j in range(1, self.ncolumns) ])
            self.data.append(row)

        with NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as fp:
            row = ";".join(map(str, self.header))
            print(row, file=fp)
            for record in self.data:
                row = ";".join(map(str, record))
                print(row, file=fp)
            self.filename = fp.name

    def tearDown(self):
        remove(self.filename)

    def test_length(self):
        results = get_results(self.filename, keyname='column 0')
        self.assertEqual(self.nrecords, len(results))

    def test_content_dict(self):
        results = get_results(self.filename, keyname='column 0')
        head = self.header[1:]
        for row in self.data:
            key = str(row[0])
            val = row[1:]
            self.assertTrue(key in results)
            record = results[key]
            for i,k in enumerate(head):
                self.assertTrue(k in record)
                self.assertEqual(record[k], str(val[i]))

    def test_content_list(self):
        results = get_results(self.filename)
        for row in self.data:
            key = str(row[0])
            val = [str(x) for x in row[1:]]
            self.assertTrue(key in results)
            record = results[key]
            self.assertEqual(val, record)


class TestComposeBody(unittest.TestCase):

    def setUp(self):
        self.values = {
            'abc':123,
            'XXX':-1,
            '777':999}
        body = """preamble
        @abc@
        @777@
        @noreplacement@
        epilogue"""
        with NamedTemporaryFile(mode='w', delete=False) as fp:
            fp.write(body)
            self.filename = fp.name

    def tearDown(self):
        remove(self.filename)

    def test_normal_text(self):
        rendered = compose_body(self.filename, self.values)
        self.assertTrue(rendered.startswith('preamble'))
        self.assertTrue(rendered.endswith('epilogue'))

    def test_replace(self):
        rendered = compose_body(self.filename, self.values)
        self.assertTrue(" abc:\t123\n" in rendered)
        self.assertTrue(" 777:\t999\n" in rendered)

    def test_no_replace(self):
        rendered = compose_body(self.filename, self.values)
        self.assertTrue(" @noreplacement@\n" in rendered)

    def test_no_entry(self):
        rendered = compose_body(self.filename, self.values)
        self.assertTrue(" XXX:\t-1\n" not in rendered)


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
        pattern = re.compile("^Content-Disposition: attachment;", re.M)
        count = 0
        for match in pattern.finditer(txt):
            count += 1
        self.assertEqual(count, 2)


class TestText(unittest.TestCase):

    def setUp(self):
        self.ascii = b'abAB -+\t12&*(]'
        self.utf8 = b'abAB \xc4\x85\xc4\x99\xc5\xbb\xc5\x81\t12&*(]'

    def test_ascii(self):
        text = self.ascii.decode('ASCII')
        mimeobj = Text(text, _subtype='plain')
        out = mimeobj.as_string()
        pat = re.compile('^Content-Type:.*charset="us-ascii"$', re.M)
        self.assertTrue(pat.search(out))
        tmp = out.splitlines()
        self.assertEqual(tmp[-1], text)

    def test_utf8(self):
        text = self.utf8.decode('UTF-8')
        mimeobj = Text(text, _subtype='plain')
        out = mimeobj.as_string()
        pat = re.compile('^Content-Type:.*charset="utf-8"$', re.M)
        self.assertTrue(pat.search(out))
        tmp = out.splitlines()
        tmp = b64decode(tmp[-1])
        self.assertEqual(tmp, self.utf8)


if __name__ == '__main__':
    unittest.main()
