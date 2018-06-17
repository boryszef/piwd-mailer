from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import mimetypes
import getpass
import smtplib
import csv
import re
from time import sleep
from collections import namedtuple

# Global setup
testResults = "wyniki.csv"
emailFrom = "X Y <x@y.com>"
emailSubject = "blah"
fileBody = "email.txt"
mailServer = "smtp.example.com"
mailUser = "robot"
dryRun = False


class Score(object):
    """Store decimal numbers as integers and convert them to grades
    directly, taking care of correct comparison.

    Rationale:
    Suppose the student needs 10.3 points to pass.
    score = 10.2
    score += 0.1
    The student should pass, however floating point arithmetics
    gives score = 10.299999999999999 and the comparison
    score >= 10.3
    produces False."""

    precision = 1

    grading = [
        (-4, 15, "2.0", "niedostateczny"),
        (15, 17.5, "3.0", "dostateczny"),
        (17.5, 20, "3.5", "dostateczny+"),
        (20, 22.5, "4.0", "dobry"),
        (22.5, 25, "4.5", "dobry+"),
        (25, 27.5, "5.0", "bardzo dobry"),
        (27.5, 30, "5.5", "celujący"),
    ]

    def __init__(self, val):
        if isinstance(val, str):
            val = float(val)
        if isinstance(val, int):
            val *= Score.factor()
        elif isinstance(val, float):
            val = round(val * Score.factor())
        if not isinstance(val, int):
            raise TypeError("Accepted types are int, float and str")
        self.value = val

    @classmethod
    def factor(cls):
        """Returns factor to shift decimal point of the number"""
        return 10**cls.precision

    def __float__(self):
        return float(self.value / Score.factor())

    def __str__(self):
        return "{:.1f}".format(float(self))

    def __repr__(self):
        return "Score('{}')".format(str(self))

    def __eq__(self, other):
        if not isinstance(other, Score):
            other = Score(other)
        return True if self.value == other.value else False

    def __gt__(self, other):
        if not isinstance(other, Score):
            other = Score(other)
        return True if self.value > other.value else False

    def __le__(self, other):
        if not isinstance(other, Score):
            other = Score(other)
        return True if self.value <= other.value else False

    def get_grade(self):
        """Return a tuple containing the numerical and textual
        grade corresponding to the score, both as str type."""

        for grade in self.grading:
            low = grade[0]
            high = grade[1]
            if self > low and self <= high:
                return grade[2], grade[3]
        raise RuntimeError("Value is outside grading boundaries")


def compose_body(body_file, results):
    with open(body_file) as fp:
        body = fp.read()
    for k, v in results.items():
        pat = "@{}@".format(k)
        repl = "{}:\t{}".format(k, v)
        body = body.replace(pat, repl)
    return body


def get_results(filename, keyname=None, delimiter=';', quotechar='"'):

    """Read results from a CSV file and return as dictionary. If `keyname`
    is not None, the file is expected to contain column names in the first
    row, the records are returned as dictionaries and the indicated
    column `keyname` is used as an unique key. Otherwise, the first column
    is used as an unique key, and the remaining fields are returned
    as list."""

    results = {}
    with open(filename) as fp:
        if keyname:
            func = csv.DictReader
        else:
            func = csv.reader
        reader = func(fp, delimiter=delimiter, quotechar=quotechar)
        for row in reader:
            if keyname is None:
                idx = row[0]
                val = row[1:]
            else:
                val = {}
                while row:
                    tmp = row.popitem()
                    if tmp[0] == keyname:
                        idx = tmp[1]
                    else:
                        val[tmp[0]] = tmp[1]
            results[idx] = val
    return results


MType = namedtuple('MType', ['type', 'encoding', 'maintype', 'subtype'])


class Text(MIMEText):
    """Create MIMEText object encoded as _charset. If _charset
    is None, try ASCII first, then UTF-8."""

    def __init__(self, text, _subtype='plain', _charset=None):

        if _charset is None:
            try:
                text.encode('US-ASCII')
                _charset = 'US-ASCII'
            except UnicodeEncodeError:
                _charset = 'UTF-8'
        super(Text, self).__init__(text, _subtype, _charset)


class Message(MIMEMultipart):

    def __init__(self, fromaddr, toaddr, subject, bodyplain=None,
                 bodyhtml=None, attachments=[]):

        super(Message, self).__init__()
        self['Subject'] = subject
        self['From'] = fromaddr
        if isinstance(toaddr, str):
            toaddr = [toaddr]
        self['To'] = ", ".join(toaddr)
        self.preamble = 'This is a multi-part message in MIME format.'

        attachment_types = {}
        for att in attachments:
            ctype, encoding = mimetypes.guess_type(att)
            if ctype is None:
                raise RuntimeError("Could not guess the MIME type")
            maintype, subtype = ctype.split('/', 1)
            attachment_types[att] = MType(ctype, encoding, maintype, subtype)

        if bodyplain:
            text = MIMEText(bodyplain, _subtype='plain')

        if bodyhtml:
            image_cid = {}
            idx = 0
            for aname, atypes in attachment_types.items():
                if atypes.maintype != 'image':
                    continue
                cid = "image{}".format(idx)
                idx += 1
                pattern = 'src\s*=\s*"{}"'.format(aname)
                substitute = 'src="cid:{}"'.format(cid)
                bodyhtml = re.sub(pattern, substitute, bodyhtml,
                                  re.IGNORECASE | re.MULTILINE)
                image_cid[aname] = cid
            html = MIMEText(bodyhtml, _subtype='html')

        if bodyplain and bodyhtml:
            alternative = MIMEMultipart('alternative')
            alternative.attach(text)
            alternative.attach(html)
            self.attach(alternative)
        elif bodyplain:
            self.attach(text)
        elif bodyhtml:
            self.attach(html)
        else:
            raise RuntimeError("plain text or html message must be present")

        for atname, attype in attachment_types.items():
            if attype.maintype == 'image':
                with open(atname, 'rb') as atfile:
                    atm = MIMEImage(atfile.read(), _subtype=attype.subtype)
                    if atname in image_cid:
                        cid = image_cid[atname]
                        atm.add_header('Content-ID', '<{}>'.format(cid))
            elif attype.maintype == 'text':
                with open(att) as atfile:
                    atm = MIMEText(atfile.read(), _subtype=attype.subtype)
            else:
                raise NotImplementedError(
                    "{} attachments are not implemented".format(attype.ctype))
            atm.add_header('Content-Disposition', 'attachment',
                           filename=atname)
            self.attach(atm)


class Sender(object):

    def __init__(self, server, user, password, dry_run=False):

        self.dry_run = dry_run
        self.server = server
        self.user = user
        self.password = password

    def __enter__(self):
        if not self.dry_run:
            self.smtp = smtplib.SMTP(self.server, 587)
            self.smtp.ehlo()
            self.smtp.starttls()
            self.smtp.login(self.user, self.password)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.dry_run:
            self.smtp.quit()

    def send(self, msg):
        """Actually send the message or return text if dry run"""
        if not self.dry_run:
            self.smtp.send_message(msg)
        else:
            return msg.as_string()


if __name__ == '__main__':

    mailPassword = getpass.getpass("Enter mailbox password:")

    data = get_results(testResults, 'ID')

    with Sender(mailServer, mailUser, mailPassword, dryRun) as snd:
        for student, results in data.items():
            body = compose_body(fileBody, results)
            to = "%s@student.pwr.edu.pl" % student
            print("Sending to", to)
            msg = Message(emailFrom, to, emailSubject, body)
            out = snd.send(msg)
            if out:
                print(out)
            # let the mail server take a breath
            sleep(2)
